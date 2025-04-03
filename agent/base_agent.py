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
        db_client = mysql.connector.connect(
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
            "macro_tool": MacroTool(db_client=db_client),
            "financial_tool": FinancialTool(),
            "stock_tool": StockTool(db_client=db_client),
            "sector_tool": SectorTool(
                mysql_url=mysql_url, 
                mongo_url=mongo_url, 
                upstage_api_key=upstage_api_key
            ),
            "pdf_tool": PDFTool(),
        }
        
        return tools

    def _query_tool(self, tool_name: str, **kwargs) -> Any:
        """등록된 툴을 호출"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        tool = self.tools[tool_name]
        return tool.run(**kwargs)

    def _call_llm(self, prompt: str) -> str:
        """
        이미 완성된 프롬프트 문자열을 LLM에 전달하여 결과를 반환합니다.
        """
        # 설정 파일에서 API 키 가져오기
        config = load_config(config_path='./config/config.yaml')
        api_key = config['upstage']['api_key']
        
        client = OpenAI(api_key=api_key, 
                        base_url="https://api.upstage.ai/v1",)
        
        stream = client.chat.completions.create(
            model='solar-pro', 
            messages=[
                {"role": "user", 
                 "content": prompt
                 }
                ],
            stream = False)
        
        # LLMManager를 사용하여 모델 호출

        return stream.choices[0].message.content
    
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