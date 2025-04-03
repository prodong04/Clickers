
from openai import OpenAI  # openai==1.52.2
from config.config_loader import load_config  # 설정 파일 로드 함수


class LLMManager:
    # GPU 디바이스 결정
    device = 'cpu'
    
    # 공유 인스턴스 변수
    text_llm = None
    text_tokenizer = None
    vlm_model = None
    vlm_processor = None
    openai_client = None

    @classmethod
    def initialize_openai_client(cls):
        """
        OpenAI Client 초기화
        """
        if cls.openai_client is None:
            config = load_config(config_path='./config/config.yaml')
            api_key = config['upstage']['api_key']
            cls.openai_client = OpenAI(
                api_key=api_key,
                base_url="https://api.upstage.ai/v1"
            )
        return cls.openai_client

    @classmethod
    def get_text_llm(cls, model_name: str = "solar-pro"):
        """
        텍스트 생성용 LLM을 로드합니다 (OpenAI API 사용).
        """
        cls.initialize_openai_client()
        
        def chat(prompt: str, stream: bool = False):
            """
            OpenAI API로 텍스트 생성 요청 보내기.
            """
            messages = [{"role": "user", "content": prompt}]

            response = cls.openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=stream
            )

            
            if stream:
                response_text = ""
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        response_text += chunk.choices[0].delta.content
                        print(chunk.choices[0].delta.content, end="")
                return response_text
            else:
                return response.choices[0].message.content.strip()

        return chat
