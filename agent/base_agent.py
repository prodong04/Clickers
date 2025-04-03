import abc
from typing import Any, Dict, Optional
from tools.price_tool import PriceTool
from tools.financial_tool import FinancialTool
from tools.macro_tool import MacroTool
from tools.sector_tool import SectorTool
from tools.stock_tool import StockTool
from tools.pdf_tool import PDFTool
from openai import OpenAI  # openai==1.52.2

import mysql.connector
from config.config_loader import load_config





class BaseAgent(abc.ABC):
    """
    모든 Agent가 공통으로 가져야 할 메서드 및 속성을 정의한 추상 클래스.
    """
    def __init__(self, name: str, model_name: str, config: Dict[str, Any]):
        self.name = name
        self.model_name = model_name
        self.config = config
        self.tools = self._register_tools()  # 자동 등록

    def _register_tools(self) -> Dict[str, Any]:
        """
        사용할 Tool을 자동 등록
        """
        # 설정 파일 로드
        config = load_config(config_path='./config/config.yaml')
        
        # 데이터베이스 및 API 정보 불러오기
        mysql_config = config['mysql']
        mongo_config = config['mongo']
        upstage_config = config['upstage']

        # MySQL 데이터베이스 연결 설정
        self.db_client = mysql.connector.connect(
            user=mysql_config['user'],
            password=mysql_config['password'],
            host=mysql_config['host'],
            port=mysql_config['port'],
            database=mysql_config['database']
        )
        
        # URL 정보 추출
        mysql_url = mysql_config['url']
        mongo_url = mongo_config['url']
        upstage_api_key = upstage_config['api_key']

        # 툴 딕셔너리 생성
        tools = {
            "price_tool": PriceTool(),
            "macro_tool": MacroTool(),
            "financial_tool": FinancialTool(),
            "stock_tool": StockTool(),
            "sector_tool": SectorTool(),
            "pdf_tool": PDFTool(),
        }
        
        return tools

    def _query_tool(self, tool_name: str, **kwargs) -> Any:
        """등록된 툴을 호출"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        tool = self.tools[tool_name]
        return tool.run(**kwargs)
    
    def _call_critic_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """
        이미 완성된 프롬프트 문자열을 LLM에 전달하여 결과를 반환합니다.
        """
        # 설정 파일에서 API 키 가져오기
        config = load_config(config_path='./config/config.yaml')
        api_key = config['upstage']['api_key']
        
        client = OpenAI(api_key=api_key, 
                        base_url="https://api.upstage.ai/v1",)
        
        system_prompt = """

                                ## 1. 보고서 타당성 평가
                                - 이 섹션에서는 전체 보고서를 읽고, 잘못된 정보나 모호한 부분이 있으면 구체적으로 지적합니다.
                                - 예시:
                                - 잘못된 정보: 매출 성장률이 잘못 계산되었습니다. (제시된 데이터: 10%, 실제 계산: 8.5%)
                                - 모호한 부분: 리스크 분석에서 외부 요인의 영향이 불충분하게 다뤄졌습니다.

                                ## 2. 수정 요청
                                - 만약 보고서에 수정할 부분이 있다면, 아래와 같은 형식으로 작성하세요.
                                - `수정 요청을 해주세요`: 기업 개요에서 제공된 데이터와 실제 분석 내용이 일치하지 않습니다. 데이터 정확성을 확인하고 수정해 주세요.
                                - 만약 수정 사항이 없다면, 이 섹션은 비워둡니다. 절대로 `수정 요청`이라는 단어를 사용하지 마세요.

                                ## 3. 최종 의견
                                - 이 섹션에서는 매수, 매도, 또는 보류 의견을 제시합니다.
                                - 만약 매수 의견을 제시한다면, 반드시 `매수 요청`이라는 단어를 포함시켜야 합니다.
                                - 예시:
                                - 매수 요청: 이 보고서는 긍정적인 투자 의견을 제시할 충분한 근거를 제공합니다. 따라서 매수 요청을 권장합니다.
                                - 매도 의견: 리스크가 지나치게 높고 근거가 부족하므로 매수 요청을 권장하지 않습니다.
                                - 보류 의견: 추가적인 데이터 분석이 필요하므로 매수 요청을 권장하지 않습니다.
                                """
                                    
        
        result = client.chat.completions.create(
            model='solar-pro', 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            stream=False)
        
        # 응답에서 텍스트 추출
        return result.choices[0].message.content

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
            """
            이미 완성된 프롬프트 문자열을 LLM에 전달하여 결과를 반환합니다.
            """
            # 설정 파일에서 API 키 가져오기
            config = load_config(config_path='./config/config.yaml')
            api_key = config['upstage']['api_key']
            
            client = OpenAI(api_key=api_key, 
                            base_url="https://api.upstage.ai/v1",)
            
            system_prompt = """너는 투자 보고서를 작성하는 금융 애널리스트입니다.
                                항상 정확히 다음 마크다운 형식으로 보고서를 작성해야 합니다:

                                # [종목명] ([종목코드]) AI 투자 보고서
                                ## ✅ 매수/매도 의견
                                - 💡 의견: [매수/매도/보유] ([BUY/SELL/HOLD])
                                - 투자 기간: [n]개월
                                - 투자 전략: [전략 요약]

                                ## 💡 투자 시사점
                                - [시사점 1]
                                - [시사점 2]
                                - [시사점 3]

                                ## 📊 장단점 기반 판단 근거
                                ✅ 장점
                                - [장점 1]
                                - [장점 2]
                                - [장점 3]

                                ❌ 단점
                                - [단점 1]
                                - [단점 2]
                                - [단점 3]

                                ## 📈 종합 의견
                                - [종합 의견 1]
                                - [종합 의견 2]

                                ## 📊 리스크 대응 방안
                                - [대응 방안 1]
                                - [대응 방안 2]

                                위 구조를 정확히 따라야 합니다. 들여쓰기 없이 마크다운 형식을 정확히 작성하세요."""
                                    
            
            result = client.chat.completions.create(
                model='solar-pro', 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                stream=False)
            
            # 응답에서 텍스트 추출
            return result.choices[0].message.content
    
    def _call_llm_structured(self, prompt: str, response_structure) -> str:
                # 설정 파일에서 API 키 가져오기
        config = load_config(config_path='./config/config.yaml')
        api_key = config['upstage']['api_key']
        
        client = OpenAI(api_key=api_key, 
                        base_url="https://api.upstage.ai/v1",)
        
        response = client.chat.completions.create(
            model='solar-pro', 
            messages=[
                {"role": "user", 
                 "content": prompt
                 }
                ],
            response_format=response_structure,
            
            
            
            stream = False)

        return response.choices[0].message.content


if __name__ == '__main__':
    # 예시로 BaseAgent 인스턴스 생성
    # agent = BaseAgent(name="TestAgent", model_name="gpt-3.5-turbo", config={})
    # print(agent.name)
    # print(agent.model_name)
    # print(agent.config)
    # print(agent.tools)
    # agent._call_llm("Hello, how are you?")
    pass