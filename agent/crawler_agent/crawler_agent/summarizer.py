import re
import os
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
load_dotenv()

def clean_response(response_text):
    """
    LLM 응답 텍스트를 정제하는 함수
    
    Args:
        response_text (str): LLM에서 반환된 원본 응답 텍스트
        
    Returns:
        str: 정제된 텍스트
    """
    # 앞뒤 공백 제거
    cleaned = response_text.strip()
    
    # 코드 블록 마커 제거 (```json, ``` 등)
    cleaned = re.sub(r'```[a-z]*\n', '', cleaned)
    cleaned = re.sub(r'```', '', cleaned)
    
    # 불필요한 큰따옴표 제거
    cleaned = cleaned.replace('\"', '"')
    
    # 불필요한 여러 줄 바꿈 단일 줄 바꿈으로 변경
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned

def summarization(text, category="stock", model_name="solar-pro-241126", temperature=0.7, client=None):
    """
    DB에서 가져온 텍스트를 Solar Pro API를 통해 요약하는 함수
    
    Args:
        text (str): 요약할 텍스트
        category (str): "stock" 또는 "sector"
        model_name (str): 사용할 모델 이름, 기본값은 'solar-pro-241126'
        temperature (float): 
        client: API 클라이언트 (없으면 새로 생성)
        
    Returns:
        str: 요약된 텍스트
    """
    # OpenAI 호환 클라이언트가 없으면 생성
    if client is None:
        client = OpenAI(
            api_key=os.getenv("UPSTAGE_API_KEY"),
            base_url="https://api.upstage.ai/v1"
        )
    
    # 텍스트 전처리 없이 그대로 사용
    full_text = text
    
    # 프롬프트 템플릿 설정
    stock_prompt = PromptTemplate.from_template(
    """Based on the provided text, reformat the text according to the following guidelines:
    
    Output the result in the following format:
    0. 종목 키워드: [extracted keywords]
    1. 종목 설명: [detailed description of the stock]

    Document:
    {split_documents}"""
    )

    sector_prompt = PromptTemplate.from_template(
    """Based on the provided text, reformat the text according to the following guidelines:
    
    Output the result in the following format:
    0. 종목 키워드: [extracted keywords]
    1. 내용 요약: [A concise summary capturing the core insights of the report in a few clear sentences]

    Document:
    {split_documents}"""
    )

    prompt_template = stock_prompt if category == "stock" else sector_prompt
    prompt_text = prompt_template.format(split_documents=full_text)

    # API 호출로 요약 생성
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an AI assistant specializing in document summarization."},
            {"role": "user", "content": prompt_text}
        ],
        temperature=temperature
    )

    # 응답에서 텍스트 추출
    response_text = response.choices[0].message.content
    cleaned_text = clean_response(response_text)
    
    return cleaned_text