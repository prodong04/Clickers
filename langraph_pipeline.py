import os
import json
import datetime
import pandas as pd
from typing import Dict, Optional
import operator

# LangGraph 관련 모듈
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

# 에이전트 및 도구 임포트
from agent.analyst_agent import AnalystAgent
from agent.critic_agent import CriticAgent
from agent.fundmanager_agent import FundManagerAgent
from tools.pdf_tool import PDFTool
from typing import TypedDict
from langchain_core.documents import Document
from config.config_loader import load_config
import mysql.connector

# 에이전트 인스턴스 생성
analyst_agent = AnalystAgent(name="AnalystAgent", model_name="solar-pro", config={})
critic_agent = CriticAgent(name="CriticAgent", model_name="solar-pro", config={})
fund_manager_agent = FundManagerAgent(name="FundManagerAgent", model_name="solar-pro", config={})
pdf_tool = PDFTool()

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
       


def get_ticker(start_date, end_date)-> list:
    cursor = db_client.cursor(dictionary=True)
    query = """
        SELECT DISTINCT ticker, stock_name
        FROM stock_reports
        WHERE date BETWEEN %s AND %s;
    """
    cursor.execute(query, (start_date, end_date))
    result = cursor.fetchall()


    return result





# GraphState 정의 (각 티커별 상태)
class GraphState(TypedDict):
    ticker: str
    context: Dict        # 에이전트의 보고서 데이터 저장
    feedback: Optional[str]
    risk_preference: str
    lookback: int
    start_date: str
    end_date: str
    accepted: bool
    iterate: int         # 반복 횟수

def check_logic(state: GraphState) -> str:
    """
    상태가 논리적인지 판단하여 문자열 조건 반환:
    - "end": 종료 조건 (반복 횟수 초과 또는 피드백 없이 승인된 경우)
    - "loop": 반복 필요 (피드백이 있고 승인되지 않은 경우)
    """
    state['iterate'] += 1  # 반복 횟수 증가
    # 예시: 반복 횟수가 4회를 초과하면 종료
    if state['iterate'] > 4:
        return "end"
    # 피드백이 존재하고 승인되지 않은 경우 반복
    if state['feedback'] is not None and not state['accepted']:
        return "loop"
    # 피드백이 없고 승인된 경우 종료
    elif state['accepted']:
        return "end"
    return "loop"  # 기본적으로 반복

# AnalystAgent 실행 노드
def analyst_agent_func(state: GraphState) -> GraphState:
    report = analyst_agent.run(
        ticker_list=[state["ticker"]],
        risk_preference=state["risk_preference"],
        lookback=state["lookback"],
        start_date=state["start_date"],
        end_date=state["end_date"],
        feedback=state.get("feedback")
    )
    state["context"] = report  # 단일 티커에 대한 보고서 저장
    print(f"[INFO] Analyst report for {state['ticker']}: {report}")
    return state

# CriticAgent 실행 노드
def critic_agent_func(state: GraphState) -> GraphState:
    critic_report = critic_agent.run(analyst_report=state["context"])
    revise = critic_report.get('revise', False)
    if revise:
        state["feedback"] = critic_report.get('critic', "피드백 필요")
        state["accepted"] = False
    else:
        state["accepted"] = True
    print(f"[INFO] Critic report for {state['ticker']}: {critic_report}")
    return state

# 워크플로우 구성: analyst와 critic 노드만 포함하는 피드백 루프
workflow = StateGraph(GraphState)
workflow.add_node('analyst', analyst_agent_func)
workflow.add_node('critic', critic_agent_func)
workflow.add_edge('analyst', 'critic')  # AnalystAgent의 보고서를 CriticAgent에 전달

# Critic 노드에서 조건부 엣지를 통해 상태에 따라 analyst로 돌아갈지 결정
workflow.add_conditional_edges('critic', 
                               check_logic,
                               {
                                  "end": END,
                                  "loop": 'analyst'
                               })
workflow.set_entry_point('analyst')  # 시작 노드 설정

app = workflow.compile()

# 파라미터 설정
start_date = "2025-03-21"
end_date = "2025-03-28"
risk_preference = "나는 아주 공격적인 투자자야. 리스크를 매우 선호하고, 그만큼 고수익을 원해."
lookback = 200

ge = get_ticker(start_date=start_date, end_date=end_date)

# 테스트용 티커 목록
ticker_list = sorted(pd.DataFrame(ge)['ticker'].tolist())

# 결과 저장 디렉토리 생성
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
parent_dir = os.path.join(os.getcwd(), f"run_{timestamp}")
os.makedirs(parent_dir, exist_ok=True)
stock_dir = os.path.join(parent_dir, "stock")
os.makedirs(stock_dir, exist_ok=True)
print(f"[INFO] Created parent directory: {parent_dir}")
print(f"[INFO] Created stock directory: {stock_dir}")

# 각 티커별 최종 Critic 보고서를 저장할 딕셔너리
final_reports: Dict[str, dict] = {}

# 각 티커별 analyst-critic 피드백 루프 실행
for ticker in ticker_list:
    print(f"\n[INFO] Processing ticker: {ticker}")
    initial_state: GraphState = {
        "ticker": ticker,
        "context": {},
        "feedback": None,
        "risk_preference": risk_preference,
        "lookback": lookback,
        "start_date": start_date,
        "end_date": end_date,
        "accepted": False,
        "iterate": 0
    }
    final_state = app.invoke(initial_state)
    final_reports[ticker] = final_state["context"]
    break  # 테스트를 위해 첫 티커만 처리
breakpoint()
# 루프 종료 후, FundManagerAgent에 최종 Critic 보고서를 전달하여 최종 판단 실행
fund_manager_result = fund_manager_agent.run(final_reports, start_date, end_date)  
print(f"[INFO] FundManagerAgent 최종 결과: {fund_manager_result}")
# fund_manager_result = {
#     "ticker": {
#         "final_decision": True,
#         "reason": "편입을 찬성합니다."
#     }
# }
            

# 각 티커별로 Critic 보고서를 PDF로 생성
for ticker, _ in fund_manager_result.items():
    analyst_report = final_reports[ticker]
    ticker_pdf_filename = os.path.join(stock_dir, f"{ticker}_critic_report.pdf")
    critic_content = analyst_report.get("analysis", "최종 보고서")
    pdf_result = pdf_tool.run(
        report_data=critic_content,
        filename=ticker_pdf_filename,
        report_type="critic"
    )
    print(f"[INFO] Report PDF generated for {ticker}: {pdf_result}")

# 전체 최종 결과를 JSON 파일로 저장 (펀드매니저 최종 결과 포함)
report_json = {
    "analyst_reports": final_reports,
    "fund_manager_result": fund_manager_result
}
report_json_filename = os.path.join(parent_dir, "final_reports.json")
with open(report_json_filename, "w", encoding="utf-8") as f:
    json.dump(report_json, f, ensure_ascii=False, indent=4)
print(f"[INFO] Saved final reports as JSON: {report_json_filename}")

# 종목 리스트를 end_date 이름으로 폴더 생성
output_folder = os.path.join(parent_dir, end_date)
os.makedirs(output_folder, exist_ok=True)
print(f"[INFO] Created folder for saving CSV files: {output_folder}")

tickers = list(final_reports.keys())

# 데이터프레임 생성 (각 종목 티커를 value로 저장)
df = pd.DataFrame({
    'value': tickers
})
df.index = [end_date] * len(tickers)  # 인덱스를 end_date로 설정
df.index.name = 'index'

# CSV 파일 저장 경로 설정
csv_file_path = os.path.join(output_folder, f"{end_date}.csv")

# CSV 파일로 저장
df.to_csv(csv_file_path, index=True, encoding='utf-8-sig')
print(f"[INFO] Saved CSV file: {csv_file_path}")

# 워크플로우 그래프 시각화 (옵션)
graph_png = workflow.get_graph(xray=True).draw_mermaid_png()
graph_png_filename = os.path.join(parent_dir, "workflow_graph.png")
with open(graph_png_filename, "wb") as f:
    f.write(graph_png)
print(f"[INFO] Saved workflow graph visualization as PNG: {graph_png_filename}")
