from typing import Any, Dict
from .base_agent import BaseAgent

class FundManagerAgent(BaseAgent):
    """
    매수/매도 의견 및 수정된 분석 내용을 바탕으로 최종 펀드 편입 여부를 결정합니다.
    결과는 **마크다운** 형식의 리포트로 작성됩니다.
    """
    def run(self, critic_report: Dict[str, Any], start_date, end_date) -> Dict[str, Any]:
        decisions = {}
        macro_data = self._query_tool("macro_tool", start_date=start_date, end_date=end_date)
        for ticker, data in critic_report.items():
            print(f"\n[INFO] 📌 FundManagerAgent: 최종 평가 시작 - 종목코드 = {ticker}")

            opinion = data["analysis"]
            
            print(f"[DEBUG] 🧮 매크로 데이터: {macro_data}")

            
            print(f"[DEBUG] 📝 크리틱 요약 의견: {opinion}")

            # print(f"[DEBUG] 🌐 매크로 데이터: {macro_data}")
                    # {macro_data}
            
            prompt = f"""
                        # 펀드 최종 평가 및 편입 결정

                        다음 정보를 참고하여 **펀드 편입 여부**를 결정해 주세요.

                        ## 기본 정보
                        - **종목코드**: {ticker}
                        - **매크로 요약**:
                

                        ## 애널리스트 크리틱 리포트 요약
                        - **애널리스트 크리틱 요약 의견**:
                        {opinion}



                        ## 평가 지침
                        리스크 선호도가 **공격적**임을 고려하여, 펀드에 편입할 경우 반드시 **'편입을 찬성합니다.'**이라는 단어를 포함한 응답을 작성해 주세요.  
                        편입하지 않을 경우, **'편입을 찬성합니다.'** 단어를 포함하지 않고 리포트를 작성해 주세요.

                        최종적으로, 펀드 편입 여부와 그 사유를 **마크다운** 형식으로 작성해 주세요.
                        """
            # print(f"[DEBUG] 🚦 생성된 FundManager 프롬프트 (일부): {prompt[:500]}...")
            
            fund_manager_response = self._call_llm(prompt)
            print(f"[INFO] 🔍 FundManagerAgent 응답 (LLM 결과):\n{fund_manager_response}")
            
            # 응답에 "찬성" 단어가 포함되어 있으면 편입(True), 아니면 미편입(False)
            final_decision = "편입을 찬성합니다." in fund_manager_response
            decisions[ticker] = {
                "final_decision": final_decision,
                "reason": fund_manager_response
            }
            
            print(f"[RESULT] 📊 최종 결정: {'편입' if final_decision else '미편입'}")
        
        #최종 
        print(f"#### 📝 FundManagerAgent 결과 : {decisions}")
        return decisions
