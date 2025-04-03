# agents/analyst_agent.py
from typing import Any, Dict
from .base_agent import BaseAgent
import logging

class AnalystAgent(BaseAgent):
    """
    종목별 리포트를 생성하는 AnalystAgent.
    피드백이 주어지면 이를 반영하여 보고서를 재작성할 수 있습니다.
    """
    def __init__(self, name, model_name: str, config: dict):
        super().__init__(name=name, model_name=model_name, config=config)

    def run(self, ticker_list: list, risk_preference: str, lookback: int, start_date, end_date, feedback: str = None) -> Dict[str, Any]:
        for ticker in ticker_list:
            print(f"\n[INFO] 📌 분석 시작: 종목코드 = {ticker}")

            # 1) 매크로 정보
            macro_data = self._query_tool("macro_tool", start_date=start_date, end_date=end_date)
            # print(f"[DEBUG] 🧮 매크로 데이터: {macro_data}")


            sector_data = self._query_tool("sector_tool", ticker = ticker, top_k=5, days_ago=14, days_lookback=14, score_threshold=0.4)
            # print(f"[DEBUG] 🏢 섹터 데이터: {sector_data}")

            # 3) 종목 리포트
            stock_report = self._query_tool("stock_tool", ticker=ticker, start_date=start_date, end_date=end_date)
            # print(f"[DEBUG] 📄 종목 리포트: {stock_report}")

            # 4) 가격 데이터
            price_data = self._query_tool("price_tool", ticker=ticker, date=start_date, lookback=lookback)
            # print(f"[DEBUG] 📈 가격 데이터: {price_data}")

            # 5) 재무제표
            financials = self._query_tool("financial_tool", ticker=ticker)
            # print(f"[DEBUG] 💰 재무제표: {financials}")

            # --------------------------------------------------
            # 여기서부터는 'prompt'를 생성하는 부분입니다.
            # 기존 내용 + 예시 보고서를 한꺼번에 포함시켜 LLM에게 요청합니다.
            # --------------------------------------------------
            prompt = f"""
            - **역할:** 유능한 금융 애널리스트
            - **목표:** 제공된 데이터를 기반으로 논리적이고 상세한 **마크다운(Markdown)** 형식의 AI 투자 보고서 작성
            - **주의사항(매우 엄격):**
              1. 사용자의 리스크 선호도 반영: 매력도가 부족하면 매수 의견 내리지 말 것
              2. 숫자 데이터(종목 코드, 재무제표 등)는 정확히 기입할 것
              3. 예시 데이터와 제공된 실제 데이터를 절대 섞지 말 것
              4. 예시보다 더 상세하고 체계적으로 작성할 것
              5. 피드백이 있을 경우 보고서 맨 아래에 'critic : {feedback}'라고 적을 것
              6. **마크다운 형식**을 반드시 지킬 것 (위반 시 즉시 재작성)
              7. **모든 보고서는 아래의 구조(예시 보고서 구조)를 정확히 따를 것** (형식 조금이라도 다르면 안 됨)
              8. price나 financial은 숫자 그대로 복붙하지 말 것(내용을 요약, 분석한 형태로 작성)

            ---


            # 제공된 데이터 목록 (보고서 작성 시 활용해야 함) 
            - 매크로 데이터(macro_data): {macro_data}
            - 섹터 데이터(sector_data): {sector_data}
            - 종목 리포트(stock_report): {stock_report}
            - 가격 데이터(price_data): {price_data}
            - 재무제표(financials): {financials}

            위 데이터들을 활용해 분석한 후, **절대 새로운 형식을 만들지 말고** 아래 예시 보고서의  방식 그대로 맞춰서 작성하세요.
            내용은 더 디테일하고 길게 작성해야 합니다.

            # 예시 리포트 (참고용, 혼동 금지)
            *(아래는 예시일 뿐 실제 작성 시 데이터로 쓰면 안 됨)*
            *(그러나 예시와 똑같은 양식, 구조, 표현 방식을 따라야 함)*

            # 작성 요청
            아래 예시를 철저히 참고하되, **제공된 데이터**만 사용해 보고서를 작성하시오.
            예시와 혼동 없이, 예시의 형식·구조·단계·표현을 동일하게 따라 주세요.
            **형식을 어기면 즉시 다시 작성**해야 하며, **마크다운 형식**이 아니면 실패로 간주합니다.

            ### 예시:

            # 하이트진로 (000080) AI 투자 보고서
            ## ✅ 매수/매도 의견
            - 💡 의견: 매수 (BUY)
            - 투자 기간: 12개월
            - 투자 전략: 중장기 보유 추천

            ## 💡 투자 시사점
            - 소주 시장 지배력 유지 및 증류주 판매 확대
            - 경쟁사 맥주 가격 인상으로 인한 수혜 가능성
            - 비용 효율성 개선과 브랜드 마케팅 강화

            ## 📊 장단점 기반 판단 근거
            ✅ 장점
            - 시장 점유율 유지 및 증류주 판매 증가
            - 광고선전비 축소로 비용 효율성 향상
            - '켈리', '테라' 브랜드 마케팅 성공

            ❌ 단점
            - 맥주 부문 실적 부진
            - 경기 침체로 주류 시장 성장 제한
            - 원가 상승 및 환율 변동 리스크

            ## 📈 종합 의견
            - 중장기 성장 가능성 높음, 단기 리스크 존재
            - 투자 권고: 공격적 투자자에게 적합

            ## 📊 리스크 대응 방안
            - 환율 변동 모니터링
            - 원가 절감 대책 마련

            ---
            """

            # 만약 'feedback' 파라미터가 전달되었다면, prompt 끝에 피드백 반영 지시문을 추가
            if feedback:
                prompt += f"\n[피드백]\n- {feedback}\n이 피드백을 보고서에 반드시 반영하고, 보고서 마지막에 'Critic : {feedback}'를 표기하세요."



            # LLM 호출
            analysis_result = self._call_llm(prompt)
            print(f"[INFO] 🔍 분석 결과 (LLM 응답): {analysis_result}")
            results = {
                "analysis": analysis_result,
                # "raw_data": {
                #     "macro": macro_data,
                #     "sector": sector_data,
                #     "stock_report": stock_report,
                #     "price": price_data,
                #     "financials": financials
                # }
            }

        print(f'#### 📝 analysis report : {results}')

        return results


# ✅ 실행 코드 (if __name__ == "__main__")
if __name__ == "__main__":
    print("[INFO] AnalystAgent 실행 시작")

    # ✅ 에이전트 초기화
    agent = AnalystAgent(
        name="AnalystAgent",
        model_name="",
        config={}
    )

    # ✅ 분석할 종목 및 실행 조건 설정
    ticker_list = ["166090"]
    start_date = '2025-01-30'
    end_date = '2025-02-10'
    risk_preference = "공격적"
    lookback = 200

    # ✅ 분석 실행
    result = agent.run(
        ticker_list=ticker_list, 
        risk_preference=risk_preference, 
        start_date=start_date, 
        end_date=end_date, 
        lookback=lookback,
        feedback="리포트 문체를 조금 더 공식적으로 작성해 주세요."
    )

    # ✅ 결과 출력
    print("\n✅ [결과] 종목 분석 결과:")
    for ticker, data in result.items():
        print(f"\n📌 종목: {ticker}")
        print(f"🔍 분석 내용:\n{data['analysis']}")
        print(f"📊 원본 데이터:\n{data['raw_data']}")
