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
            print(f"[DEBUG] 🧮 매크로 데이터: {macro_data}")


            sector_data = self._query_tool("sector_tool", ticker = ticker, top_k=5, days_ago=14, days_lookback=14, score_threshold=0.4)
            print(f"[DEBUG] 🏢 섹터 데이터: {sector_data}")

            # 3) 종목 리포트
            stock_report = self._query_tool("stock_tool", ticker=ticker, start_date=start_date, end_date=end_date)
            print(f"[DEBUG] 📄 종목 리포트: {stock_report}")

            # 4) 가격 데이터
            price_data = self._query_tool("price_tool", ticker=ticker, date=start_date, lookback=lookback)
            print(f"[DEBUG] 📈 가격 데이터: {price_data}")

            # 5) 재무제표
            financials = self._query_tool("financial_tool", ticker=ticker)
            print(f"[DEBUG] 💰 재무제표: {financials}")

            # --------------------------------------------------
            # 여기서부터는 'prompt'를 생성하는 부분입니다.
            # 기존 내용 + 예시 보고서를 한꺼번에 포함시켜 LLM에게 요청합니다.
            # --------------------------------------------------
            prompt = f"""
                    # 시스템
                    당신은 유능한 금융 애널리스트입니다.  
                    아래의 정보를 종합하여, **마크다운(Markdown)** 형식으로 논리적이고 디테일한 AI 투자 보고서를 작성해 주세요.
                    분량은 길어도 상관 없으나, 들어가야 할 내용이 빠져서는 안됩니다. 
                    
                    매크로 데이터, 섹터 데이터, 종목 데이터, 재무제표, 가격 데이터의 흐름을 살펴봐주세요.
                    
                    # 작성 지침
                    위 예시의 흐름(투자 판단, 투자 판단 근거, 종합 의견 등)을 참고하여, **{ticker}** 종목에 대한 리포트를 **마크다운**으로 작성해 주세요.

                    ## 반드시 포함되어야 할 정보
                    1. **매수/매도 의견**
                    2. **투자 시사점**
                    3. **장단점 기반의 판단 근거**  
                    *(실적 지표, 재무 안정성, 성장성/사업성, 기술적 지표, 매크로 등)*
                    4. **종합 의견**  
                    *(장/단기 전략, 포트폴리오 내 비중, 리스크 대응 등)*

                    ## 유의사항
                    - 문체는 간결하고 핵심만 정리할 것.
                    - 종목 코드, 재무제표 등 숫자 정보가 잘못 들어가지 않도록 주의.
                    - 예시의 섹션 구성을 따르되, **{ticker}** 데이터에 맞춰서 자유롭게 서술할 것.
                    - 예시보다 더욱 자세하고 논리적으로 작성할 것.
                    - 피드백이 있다면 최종 작성 시 반영할 것.
                    - 반드시 예시와 같은 이모티콘, 마크다운으로 작성할 것. 
                    - feedback이 있다면 반드시 반영할 것.

                    ---

                    # 기본 정보
                    - **종목코드:** {ticker}
                    - **종목이름:** {stock_report[0]['stock_name']}
                    - **리스크 선호도:** {risk_preference}
                    - **분석 구간:** {start_date} ~ {end_date}
                    - **가격 데이터:** 최근 {lookback}일치

                    ---

                    # 시장 환경
                    ## 매크로 요약
                    *(종목과 관련 있어 보이는 경우에만 포함)*  
                    {macro_data}

                    ## 섹터 요약
                    *(종목과 관련 있어 보이는 경우에만 포함)*  
                    {sector_data}

                    ---

                    # 기업 개요 및 실적
                    ## 종목 리포트
                    {stock_report}

                    ## 가격 데이터 (최근 {lookback}일)
                    {price_data}

                    ## 재무제표 분석
                    {financials}

                    ---

                    # 보고서 예시

                    ## 1. 투자 판단
                    ### 매수/매도 의견
                    **매수**

                    ### 투자 시사점
                    - CJ의 실적이 약간 부진했으나, 주요 자회사의 부진은 상장 자회사의 주가 하락으로 인한 지분 가치 감소에 기인합니다.  
                    - CJ대한통운의 양호한 실적은 전체 실적 부진에 대한 압박감을 줄이고 있습니다.  
                    - 최근의 가격 데이터와 차트 분석에서 상대적으로 안정적인 추세를 보이고 있어, 장기적인 포트폴리오 구성에 활용될 만합니다.

                    ## 2. 투자 판단 근거 (장단점 포함)
                    ### 🔍 1) 실적 지표
                    #### 장점
                    - CJ대한통운의 신규 수주 확대 및 해외 사업 호조로 양호한 실적을 기록.

                    #### 단점
                    - 상장 자회사(CJ제일제당, CJENM, CJCGV)의 실적 부진으로 인한 지분 가치 감소.

                    ### 💰 2) 재무 안정성
                    #### 장점
                    - CJ대한통운의 양호한 실적은 전체 실적 부진에 대한 압박을 줄여줌.

                    #### 단점
                    - 자본이 감소하여 재무 건전성이 다소 악화됨.

                    ### 🚀 3) 성장성 / 사업성
                    #### 장점
                    - 올리브영은 방한 외국인 증가와 온라인 성장 지속으로 장기적 성장 가능성을 보유.

                    #### 단점
                    - CJ제일제당은 국내 소재 및 가공 총수요 부진으로 실적이 기대보다 낮아짐.

                    ### 📈 4) 기술적 지표 및 매수/매도 타점
                    - 현재 가격이 지지선 부근에 위치하여, 장기 투자 관점에서 매수 적기로 판단.  
                    - 단기적으로 CJ제일제당과 CJENM의 실적 부진으로 인해 변동성 확대 가능성.

                    ### 🌐 5) 매크로 및 섹터 영향 분석
                    - 미주 지역의 경쟁 강도 증가가 CJ제일제당의 실적에 부담.  
                    - 국내 소비 심리 회복이 더딘 상황에서 올리브영의 성장 둔화 가능성 존재.

                    ## 📝 종합 의견
                    - 장기적으로는 매수 의견을 유지하되, 단기 변동성에 유의하며 분할 매수 전략을 권장.  
                    - 글로벌 및 섹터 불확실성에 대비해 포트폴리오 내 비중 조절 필요.
                    ---
                    """



            # 만약 'feedback' 파라미터가 전달되었다면, prompt 끝에 피드백 반영 지시문을 추가
            if feedback:
                prompt += f"\n[피드백]\n- {feedback}\n위 피드백을 보고서에 반드시 반영해 주세요. 그리고 Critic : {feedback}라고 적어 주세요."

            # print(f"[DEBUG] 🚦 생성된 프롬프트(일부): {prompt[:500]}...")

            # LLM 호출
            analysis_result = self._call_llm(prompt)
            print(f"[INFO] 🔍 분석 결과 (LLM 응답): {analysis_result}")
            results = {
                "analysis": analysis_result,
                "raw_data": {
                    "macro": macro_data,
                    "sector": sector_data,
                    "stock_report": stock_report,
                    "price": price_data,
                    "financials": financials
                }
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
