from typing import Any, Dict
from base_agent import BaseAgent
from datetime import datetime
from pandas_datareader import data as pdr
import yfinance as yf
from datetime import datetime, timedelta, date
import sqlite3
import json
import os
import faiss
import logging
import numpy as np
from langchain_upstage import UpstageEmbeddings # pip install -qU langchain-core langchain-upstage
from langchain.prompts import PromptTemplate
from config.config_loader import load_config


# ------------------------ Logging --------------------------
logger = logging.getLogger('fund_manager_agent')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


# ------------------------ Templates ------------------------
fund_manager_template = PromptTemplate(
    input_variables=["report_summary", "macro_data", "similar_cases"],
    template="""
당신은 금융 시장의 데이터를 바탕으로 **투자 판단을 내리는 펀드매니저 역할**을 맡았습니다.  
아래에 세 가지 정보가 주어집니다:

1. 애널리스트가 분석한 의견 요약 및 그에 대한 크리틱 에이전트의 피드백  
2. 현재 시장 전반의 거시경제 상황 (예: 금리, 고용, 환율 등)  
3. 과거에 유사한 판단을 했던 사례들 (성과 포함)

이 정보를 종합적으로 이해하고 판단을 내려야 합니다.

━━━━━━━━━━━━━━━━━━━━━━  
[애널리스트 보고서 요약 및 피드백]
{report_summary}

[거시경제(매크로) 데이터]
{macro_data}

[과거 유사 판단 사례]
{similar_cases}  
━━━━━━━━━━━━━━━━━━━━━━
---

## 작성 지침 
- 과거 유사 사례가 제공되지 않을 경우에는, 애널리스트 의견과 거시경제 정보만 참고하세요.
- 아래 6단계에 맞추어 판단을 내려주세요. 각 항목마다 무엇을 써야 하는지 구체적으로 설명되어 있습니다.

---

### 1. 투자 결정  
- 아래 4가지 선택지 중에서 '현재 시점에서 어떤 행동을 할지' 결정하세요.  
    - 매수 (BUY): 지금 이 종목을 사는 것이 좋다고 판단될 때
    - 보유 (HOLD): 이미 갖고 있다면 계속 들고 있어도 된다고 판단될 때
    - 매도 (SELL): 이미 갖고 있다면 파는 것이 좋다고 판단될 때
    - 관망 (WATCH): 아직 투자 판단을 내리기 어렵고 상황을 더 지켜봐야 할 때

- 반드시 그 판단을 내린 이유를 설명하세요.
    - 단순히 ‘매출 증가가 예상되므로 매수’가 아니라,  
    - ‘왜 그러한 매출 증가가 예측되는지’,  
    - ‘어떤 조건/전제에서 그러한 결론이 나오는지’ 설명해야 합니다.

---

### 2. 주요 판단 근거 (문단 단위, 사실과 의견 구분)

- 아래 지침에 따라 3~5개의 판단 근거 문단을 작성하십시오.  
- 각 문단은 반드시 다음 구조를 따르세요:
    - 사실 (Fact):  
    리포트, 매크로 데이터, 과거 사례, 산업 분석 등 주어진 정보로부터 확인 가능한 사실을 명시하십시오.

    - 의견 (Opinion):  
    위 사실을 바탕으로 펀드매니저로서의 해석이나 추론을 명확히 작성하세요.  
    가능하면 *논리 흐름*을 포함하십시오. (예: A → B → C 구조)

- 각 판단 근거 문단에는 다음과 같은 요소들을 적절히 포함하세요:
    1. 애널리스트 리포트의 핵심 분석 포인트
    - 해당 기업의 매출/이익 추정, 전략적 변화, 경쟁 우위 등

    2. 현재 거시경제 흐름과의 관련성
    - 금리, 물가, 실업률, 환율, 통화정책 등 외부 환경이 판단에 어떤 영향을 미치는가

    3. 산업 내 경쟁/수급/포지셔닝
    - 공급망 상황, 원자재 가격, 경쟁사 대비 기술력 또는 점유율 등

    4. 정성적 요소 (필요 시 선택적으로 포함)  
    - 정책 변화, 사회적 트렌드, ESG 요소, 소비 성향 변화, 글로벌 이슈 등  
    - 예: 정부의 반도체 투자 확대, MZ세대의 소비 패턴 등

- 주의 사항  
    - “수요 증가”나 “실적 호조”처럼 두루뭉술하게 쓰지 말고, “어떤 지표로 그것을 판단했는가”를 드러내 주세요.  
    - 의견 부분은 “그렇기 때문에 매수/보유할 만하다”처럼 명확히 판단으로 연결되도록 하세요.

[예시 문단]
- 사실: 최근 발표된 미국의 소비자심리지수는 전달 대비 4.2p 상승하며 6개월 연속 개선 흐름을 보였다.  
- 의견: 이는 소비 회복이 본격화되고 있음을 시사하며, 해당 기업이 속한 내수소비 업종에도 긍정적으로 작용할 것으로 판단된다.

[예시 문단 (정성적 요소 포함)]
- 사실: 정부는 2025년까지 반도체 소재·부품 자립화를 위한 세액공제를 확대한다고 발표했다.  
- 의견: 해당 기업은 반도체 소재 기업으로, 정책 수혜 가능성이 크며 이는 투자 심리 개선 및 단기 수급에도 긍정적 영향을 줄 수 있다.


---

### 3. 리스크 요인 및 대응 전략  
- 지금 투자할 경우 발생할 수 있는 잠재적 위험요소를 1~2개 작성하고,  
- 그 리스크에 어떻게 대응하면 좋을지도 함께 적어주세요.
- 예시:
    - 리스크: 미국 금리가 다시 인상될 경우, 기술주 조정 가능성
    - 대응: 분할매수 전략 사용 또는 리스크 대비 비중 축소

---

### 4. 과거 유사 판단 사례와의 비교  
- 과거 유사 사례가 "데이터 부족"이면, 작성하지 마세요.
- 과거 유사 사례가 제공되면, 아래 항목을 포함하여 작성하세요:
    - 과거 사례와 지금 상황이 '비슷한 점'과 '다른 점'을 비교하세요:  
        - 시장 환경, 판단 이유, 결과가 어떻게 달랐는지 설명  
        - 그때 판단이 성공했는지, 실패했는지도 언급해주세요
    - 예시:
        - 유사점: 두 사례 모두 금리 하락과 기술주 상승 기대라는 전제가 있음  
        - 차이점: 당시에는 수급이 좋았지만, 현재는 외국인 매도세가 있음  
        - 결과: 당시 판단은 성공하여 1개월 후 10% 상승

---

### 5. 요약 및 포트폴리오 편입 여부  
- 위의 내용을 바탕으로 전체적인 판단을 요약하고,  
- 아래 2가지를 선택하여 작성하세요:  
    - 최종 결정: [매수 / 매도 / 보유 / 관망 중 선택]  
    - 편입 시기 제안: [즉시 / 1주 후 / 1개월 후 / 기타]
- 예시:  
    - 최종 결정: 매수  
    - 편입 시기 제안: 1주 대기 후 편입

---

### 6. 최종 판단 요약 (한 문장 선택)  
- 아래 문장 중 하나를 선택해서 마무리하세요.  
    - 이 종목은 현재 시점에서 포트폴리오에 ‘편입하는 것에 찬성’합니다.  
    - 이 종목은 현재 시점에서 포트폴리오에 ‘편입하는 것에 반대’합니다.
"""
            )

fund_feedback_template = PromptTemplate(
    input_variables=["llm_decision", "return_1w", "return_1m", "return_3m", "return_6m"],
    template=""" 
당신은 LLM 기반 펀드매니저의 판단을 평가하고, 향후 의사결정에 도움이 될 수 있는 학습 피드백을 생성하는 에이전트입니다.

[펀드매니저 판단 리포트]
--------------------------
{llm_decision}
--------------------------

[해당 리포트 이후의 실제 수익률]
- 1주 후 수익률: {return_1w}%
- 1개월 후 수익률: {return_1m}%
- 3개월 후 수익률: {return_3m}%
- 6개월 후 수익률: {return_6m}%

위 정보를 바탕으로 다음 항목을 작성하십시오.

1. 판단 구조 요약 (3줄 이내)
- 이 리포트는 어떤 가설이나 근거로 판단을 내렸는가?

2. 판단 vs 결과 비교
- 판단이 시장 수익률과 얼마나 일치했는가? 과대/과소평가 요소가 있었는가?

3. 향후 적용 가능한 교훈 (bullet point로 2~3개)
- 이 판단에서 얻을 수 있는 교훈은 무엇인가?
- 유사한 상황에서 어떤 점을 주의해야 하는가?
- 판단에서 강화하거나 보완해야 할 점은 무엇인가?

4. 한줄 총평
- 예: "중립적인 근거에 비해 수익률이 좋았으며, 리스크 요소 반영이 우수했다."
"""
)

query_rewrite_prompt = PromptTemplate(
    input_variables=["opinion"],
    template="""
당신은 LLM 기반 펀드매니저 시스템의 검색 에이전트입니다.

아래는 애널리스트 에이전트의 리포트 판단 요약과, 크리틱 에이전트의 피드백입니다. 
이 내용을 바탕으로, 유사한 과거 판단 사례를 검색하기 위한 핵심 요약 쿼리를 생성하십시오.

[애널리스트 판단 요약]
{opinion}

위 정보를 기반으로 다음 조건을 만족하는 한 단락 요약을 생성하십시오:

1. 주요 가정 또는 분석 전제 (예: "고용지표 개선", "소비심리 회복")
2. 해당 전제가 연결된 투자 판단 (예: "기술주 반등 기대", "방어주 선호")
3. 포함된 리스크 요소가 있다면 요약 포함
4. 불필요한 수사 없이, 핵심 요인 중심으로 300자 이내

[출력 예시]
"미국 고용지표 개선과 금리 동결 가능성을 근거로 기술주 상승을 예상하며, 성장 섹터 중심의 매수 의견을 제시함. 다만 인플레이션 재확산 리스크를 보완 필요."
    """
)


# ------------------------ Embedding & Index ------------------------
config = load_config(config_path='./config/config.yaml')
api_key = config['upstage']['api_key']
embeddings = UpstageEmbeddings(
    api_key=api_key,
    model="embedding-query"
)


# FAISS 인덱스 로드 또는 초기화
if not os.path.exists("db"):
    os.makedirs("db")
FAISS_INDEX_PATH = "db/vector_index.faiss"
REPORT_IDS_PATH = "db/report_ids.json"
if os.path.exists(FAISS_INDEX_PATH):
    index = faiss.read_index(FAISS_INDEX_PATH)
else:
    index = faiss.IndexFlatL2(4096)

# report_ids 로드
if os.path.exists(REPORT_IDS_PATH):
    with open(REPORT_IDS_PATH, "r") as f:
        report_ids = json.load(f)
else:
    report_ids = []


def embed_text(text, type: str = "query"):
    """
    docs임베딩은 docs라고 명시, text가 리스트로 구분되어서 들어와야함
    """
    logger.debug("Embedding text of type '%s'", type)
    if type == "docs":
        embedding = embeddings.embed_documents(text)
    else:
        embedding = embeddings.embed_query(text)
    return embedding


# ------------------------ DB + Feedback ------------------------
def save_decision(report: dict, embedding: np.ndarray):
    conn = sqlite3.connect('db/fund_manager.db')
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT,
        ticker TEXT,
        decision TEXT,
        llm_response TEXT,
        date TEXT
    )""")

    cur.execute("""
    INSERT INTO decisions (
        report_id, ticker, decision,  llm_response, date
    ) VALUES (?, ?, ?, ?, ?)
    """, (
        report["report_id"], report["ticker"], report["final_decision"],
        report["llm_response"], report["date"]
    ))

    conn.commit()
    conn.close()

    # FAISS index 업데이트: docs일 경우 임베딩이 2차원인 것 처리
    report_ids.append(report["report_id"])
    if isinstance(embedding, list):
        embedding = np.array(embedding, dtype="float32")
    if embedding.ndim == 1:
        embedding = embedding.reshape(1, -1) 
    index.add(embedding)

    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(REPORT_IDS_PATH, "w") as f:
        json.dump(report_ids, f)
    logger.info("Decision saved and index updated.")


def get_return(ticker: str, start_date: str, period: int):
    logger.debug("Getting return for %s from %s + %d weeks", ticker, start_date, period)
    end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(weeks=period)).date()
    ks_ticker = f"{ticker}.KS"
    df = yf.download(ks_ticker, start=start_date, end=end_date, progress=False)
    if df.empty:
        return None
    
    last_date_in_df = df.index[-1].date() + timedelta(days=2)
    if last_date_in_df < end_date:
        return None
    
    close_prices = df.loc[:, ('Close', ks_ticker)]
    start_price, end_price = close_prices.iloc[0], close_prices.iloc[-1]
    return round(((end_price - start_price) / start_price) * 100, 2)


def calculate_and_store_feedback(report_id, ticker, llm_response, decision_date, llm_callback):
    returns = {
        "1w": get_return(ticker, decision_date, 1),
        "1m": get_return(ticker, decision_date, 4),
        "3m": get_return(ticker, decision_date, 12),
        "6m": get_return(ticker, decision_date, 24)
    }
 
    prompt = fund_feedback_template.format(
        llm_decision=llm_response,
        return_1w=returns["1w"] or None,
        return_1m=returns["1m"] or None,
        return_3m=returns["3m"] or None,
        return_6m=returns["6m"] or None
    )
    print(f"피드백 프롬프트: {prompt}")

    feedback_summary = llm_callback(prompt)

    conn = sqlite3.connect("db/fund_manager.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT,
        return_1w REAL,
        return_1m REAL,
        return_3m REAL,
        return_6m REAL,
        feedback_summary TEXT
    )""")
    
    if all(returns[k] is not None for k in ["1w", "1m", "3m", "6m"]):
        cur.execute("""
        INSERT INTO feedback (report_id, return_1w, return_1m, return_3m, return_6m ,feedback_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            report_id, returns["1w"], returns["1m"], returns["3m"], returns["6m"],feedback_summary
        ))

    conn.commit()
    conn.close()
    logger.info("Feedback stored for report_id=%s", report_id)


def search_similar_cases(query_text: str, ticker: str, top_k: int = 1):
    if len(report_ids) < 5:
        logger.warning("Insufficient report data for similarity search.")
        return "데이터 부족"
    
    query_vec = np.array(embed_text(query_text)).astype("float32")
    D, I = index.search(np.array([query_vec]), top_k)

    similar = []
    conn = sqlite3.connect("db/fund_manager.db")
    cur = conn.cursor()

    for idx in I[0]:
        if idx >= len(report_ids):
            continue
        rid = report_ids[idx]
        cur.execute("SELECT ticker, llm_response FROM decisions WHERE report_id = ?", (rid,))
        row = cur.fetchone()
        cur.execute("SELECT feedback_summary FROM feedback WHERE report_id = ?", (rid,))
        perf = cur.fetchone()
        if row and perf:
            ticker = row[0]
            llm_response = row[1]
            feedback = perf

            similar.append(
                f"[{ticker}]의 이전 사례: {llm_response}...\n→ 실제 결과: {feedback}\n"
            )

    conn.close()
    logger.info("Found %d similar cases.", len(similar))
    return "\n".join(similar)


# ------------------------ FundManagerAgent ------------------------
class FundManagerAgent(BaseAgent):
    """
    매수/매도 의견 및 수정된 분석 내용을 바탕으로 최종 펀드 편입 여부를 결정합니다.
    결과는 **마크다운** 형식의 리포트로 작성됩니다.
    """
    def __init__(self, name, model_name: str, config: dict):
        super().__init__(name=name, model_name=model_name, config=config)

    def run(self, critic_report: Dict[str, Any], start_date, end_date) -> Dict[str, Any]:
        decisions = {}
        for ticker, data in critic_report.items():
            logger.info(f"최종 평가 시작: 종목코드 {ticker}")
            opinion = data
            macro_data = self._query_tool("macro_tool", start_date=start_date, end_date=end_date)

            
            new_query = query_rewrite_prompt.format(opinion=opinion)
            report_summary = self._call_llm(new_query)
            print(f"리포트 요약: {report_summary}")

            similar_cases = search_similar_cases(report_summary, ticker)
            print(f"유사 판단 사례: {similar_cases}")
            prompt = fund_manager_template.format(
                report_summary=report_summary,
                macro_data=macro_data,
                similar_cases=similar_cases
            )
            print(f"펀드매니저 프롬프트: {prompt}")
            fund_manager_response = self._call_llm(prompt)

            report_id = f"{ticker}_{end_date.strftime('%Y%m%d')}"
            final_decision = "찬성" in fund_manager_response
            embedding_input = [report_summary, fund_manager_response]
            embedding = embed_text(embedding_input, type="docs")
            report_data = {
                "report_id": report_id,
                "date": end_date,
                "ticker": ticker,
                "final_decision": final_decision,
                "llm_response": fund_manager_response
            }
            save_decision(report_data, embedding)
            calculate_and_store_feedback(report_id, ticker, fund_manager_response, end_date.strftime('%Y-%m-%d'), self._call_llm)
            decisions[ticker] = {"final_decision": final_decision, "reason": fund_manager_response}
            logger.info(f"[RESULT] 최종 결정: {'편입' if final_decision else '미편입'}")
        return decisions


# if __name__ == "__main__":
#     agent = FundManagerAgent(name='FM', model_name="", config={})
#     start_date = datetime.strptime("2025-02-01", "%Y-%m-%d")
#     end_date = datetime.strptime("2025-02-08", "%Y-%m-%d")
#     dummy_report = {'000150': {'analysis': '# 두산 AI 투자 보고서\n\n#### ✅ 매수/매도 의견\n- 💡 의견: 매수 (BUY)\n- 투자 기간: 12개월\n- 투자 전략: 중장기 보유 추천\n\n#### 💡 투자 시사점\n- 자체 사업 기준 4분기 별도 실적 큰 폭의 어닝 서프라이즈 예상\n- 전자 BG의 실적 상향 조정과 역대 최대 실적 기록\n- LA산불 복구 수요, 인프라 투자 등으로 25년 밥캣의 회복세\n\n#### 📊 장단점 기반 판단 근거\n✅ 장점\n- 전자 BG의 4분기 매출 최소 3,000억~3,500억원 예상\n- 미국 N사 양산 매출 발생과 믹스 개선 효과\n- 화재 이후 밥캣의 24년 실적 악화는 시장이 인지한 사실\n\n❌ 단점\n- 손자회사인 두산 밥캣의 24년 영업이익 감소 -37.3% YoY\n- 중국발 딥시크 노이즈와 투자경고로 인한 주가 변동성\n\n#### 📈 종합 의견\n- 사업 지주회사로서의 자체 실적 중요성\n- 전자 BG의 가치를 최소 4조원으로 평가\n- MSCI 편입 가능성까지 열어두며, 매수 기회로 판단\n\n#### 📊 리스크 대응 방안\n- 주가 변동성 모니터링\n- 사업 다각화 및 경쟁력 강화 대책 마련\n\n#### 🌐 시장 환경 분석\n- LA산불 복구 수요, 인프라 투자 등으로 25년 회복세 전망\n- 중국발 딥시크 노이즈와 투자경고로 인한 주가 변동성\n\n#### 🏢 기업 개요 및 실적 분석\n- 자체 사업 기준 4분기 별도 매출액은 3,950억원 (+28.5% YoY, +15.5% QoQ), 영업이익 530억원 (+700% YoY, +51% QoQ, OPM 13.4%) 예상\n- 자체 사업부는 4개 부문으로 1)전자BG, 2)두타몰, 디지털 (DDI) 및 FCP로 구성\n- 3개 사업부 합산 4분기 매출과 영업이익은 전분기와 유사한 950억원, 81억원으로 추정\n- 전자 BG 4분기 매출은 당초 우리 추정치 2,500억원을 상회한 최소 3,000억~3,500억원 (+53.8% YoY, +20.2% QoQ)에 이를 전망\n- 믹스 개선 효과로 3분기 11.9%, 4분기 13.8%의 OPM 추정\n\n#### 📅 가격 데이터 (최근 7일)\n- 디스패리티 (5일): -0.09409892333161006\n- 디스패리티 (20일): -0.019506344846376193\n- 디스패리티 (60일): 0.15536385096179747\n- 디스패리티 (120일): 0.3850167272666494\n- 종가 평균: 0.00274675447449184\n- 종가 표준편차: 0.04522574336843423\n- KOSPI 평균: -0.0009044371316980331\n- KOSPI 표준편차: 0.014119971616321255\n- 평균 거래량: 162975.13076923077\n- 거래량 표준편차: 93039.03626751203\n\n#### 📑 재무제표 분석\n- 매출액: 100,000,000,000원\n- 당기순이익: 10,000,000,000원\n- 총자산: 50,000,000,000원\n- 총부채: 20,000,000,000원\n- 현금 및 현금성자산: 5,000,000,000원\n- 장기부채: 10,000,000,000원\n- 자본: 30,000,000,000원\n- 주당순이익: 200원\n- 배당수익률: 2.0%\n- P/E 비율: 20.0\n\n#### 📈 주가 차트\n- 2024년 7월 16일부터 2025년 2월 1일까지의 주가 차트\n\n#### 📈 거래량 차트\n- 2024년 7월 16일부터 2025년 2월 1일까지의 거래량 차트\n\n#### 📈 기업 실적 차트\n- 2024년 7월 16일부터 2025년 2월 1일까지의 기업 실적 차트\n\n#### 📈 주요 지표\n- 매출액, 당기순이익, 총자산, 총부채, 현금 및 현금성자산, 장기부채, 자본, 주당순이익, 배당수익률, P/E 비율\n\n#### 📈 리스크 관리\n- 주가 변동성 모니터링\n- 사업 다각화 및 경쟁력 강화 대책 마련\n\n#### 📈 투자 전략\n- 중장기 보유 추천\n- 공격적 투자자에게 적합\n\n#### 📈 최종 의견\n- 중장기 성장 가능성 높음, 단기 리스크 존재\n- 매수 기회로 판단\n- MSCI 편입 가능성까지 열어두며, 매수 기회로 판단\n\n#### 📈 결론\n- 전자 BG의 실적 상향 조정과 역대 최대 실적 기록\n- LA산불 복구 수요, 인프라 투자 등으로 25년 밥캣의 회복세\n- 사업 지주회사로서의 자체 실적 중요성\n- MSCI 편입 가능성까지 열어두며, 매수 기회로 판단'}}

#     result = agent.run(dummy_report, start_date, end_date)
#     print("최종 결과:", result)