import re
import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.prompts import PromptTemplate


def is_numeric_line(line):
    """
    줄 전체가 숫자만으로 구성되어 있는지 판별한다.
    허용하는 문자는 숫자, 소수점(.), 콤마(,), 음수 기호(-), 퍼센트(%)
    그리고 경우에 따라 앞에 'n' 또는 'N'이 올 수 있다.
    """
    return re.fullmatch(r'[nN]?[ \t]*[-\d\.,%]+', line.strip()) is not None


def remove_tables_and_numbers(text):
    """ 테이블 및 불필요한 숫자 데이터를 제거하는 함수 """
    # 테이블 감지 및 삭제 (숫자가 연속되는 행 패턴)
    text = re.sub(r"(\d+[\t ]+\d+[\t ]+\d+[\t ]+\d+[\t ]*\d*)", "", text)  # 숫자가 많은 행 삭제
    text = re.sub(r"(\d{2,}[-/.]\d{2,}[-/.]\d{2,})", "", text)  # 날짜 형식 제거
    text = re.sub(r"\d{2,}%", "", text)  # 퍼센트 값 삭제
    text = re.sub(r"\d{5,}", "", text)  # 너무 긴 숫자(우편번호 등) 삭제
    return text.strip()


def clean_response(response,prompt_text):
    """ 모델 출력에서 불필요한 부분 제거 """
    response = response.strip()
    response = re.sub(r"\[INST\].*?\[/INST\]", "", response, flags=re.DOTALL)
    response = re.sub(r"<\|assistant\|>", "", response).strip()
    response = response.replace(prompt_text, "").strip()
    response = response.replace("*", "").strip()
    return response


def summarization(fname, category="stock", model_name="rtzr/ko-gemma-2-9b-it", temperature=0.7):
    # PDF 로딩
    loader = PyMuPDFLoader(fname)
    docs = loader.load()

    # 문서 분할 (너무 긴 입력 방지)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4096, chunk_overlap=500)
    split_documents = text_splitter.split_documents(docs)

    content = []

    # 숫자로만 이루어진 줄 제거 + 테이블 제거
    for doc in split_documents:
        lines = doc.page_content.splitlines()
        filtered_lines = [line for line in lines if not is_numeric_line(line)]
        doc.page_content = remove_tables_and_numbers("\n".join(filtered_lines))

    for s in split_documents:
        content.append(s.page_content)

    # **한 번에 모든 content를 입력**
    full_text = "\n\n".join(content)

    # **Qwen 모델용 프롬프트 설정 (테이블 삭제 지시 추가)**

    stock_prompt = PromptTemplate.from_template(
    """Based on the provided document, reformat the text according to the following guidelines:

    - Do not omit any content from the main body, including all numerical details, percentages, and units.
    - If sections such as "[ Compliance Notice ]", "[ 종목 투자등급 ]", "[ 산업 투자의견 ]" are present, they may be omitted.
    - **Remove tables and meaningless sequences of numbers before processing.**
    
    Output the result in the following format:
    0. 종목 키워드: [extracted keywords]
    1. 종목 설명: [detailed description of the stock]
    2. 내용: [reformatted document content]
    3. 애널리스트의 시사점: [analyst's insights]
    4. 시사점에 대한 근거: [supporting evidence]

    Document:
    {split_documents}"""
)

    sector_prompt = PromptTemplate.from_template(
        """Based on the provided document, reformat the text according to the following guidelines:

    - Do not omit any content from the main body, including all numerical details, percentages, and units.
    - If sections such as "[ Compliance Notice ]", "[ 종목 투자등급 ]", "[ 산업 투자의견 ]" are present, they may be omitted.
    - **Remove tables and meaningless sequences of numbers before processing.**
    
    Output the result in the following format:
    0. 종목 키워드: [extracted keywords]
    1. 내용: [reformatted document content]
    2. 애널리스트의 시사점: [analyst's insights]
    3. 시사점에 대한 근거: [supporting evidence]

    Document:
    {split_documents}"""
    )

    # Gemma 모델 로드
    prompt = stock_prompt if category == "stock" else sector_prompt

    # **💡 모델 로드 최적화 (FP16 강제 + 다중 GPU)**
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",  # 자동으로 여러 GPU에 배치
        torch_dtype=torch.float16,  # FP16 강제 적용
        offload_folder="offload",  # 부족한 경우 CPU 오프로딩
        use_cache=True  # 캐싱 활성화
    )

    generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        batch_size=32,  # 배치 크기 증가 (속도 향상)
    )

    # **💡 속도 및 출력 최적화**
    response_list = []
    # for content_chunk in content:
    prompt_text = prompt.format(split_documents=content)
    # print(content)

    result = generator(
        prompt_text,
        max_new_tokens=2048,  # 🔥 (2048 → 768)로 최적화 (속도 증가)
        temperature=temperature,
        do_sample=True,  # 🔥 샘플링 활성화 (창의적인 요약)
        top_p=0.9,  # 🔥 높은 확률의 단어만 선택
        use_cache=True,
        num_return_sequences=1
    )

    response_text = result[0]["generated_text"]
    cleaned_text = clean_response(response_text, prompt_text)
    response_list.append(cleaned_text)
    result = "\n\n".join(response_list)

    return result
