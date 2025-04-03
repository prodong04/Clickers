import os
import json
import datetime
import pandas as pd
from typing import List, Dict, Optional

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_teddynote.graphs import visualize_graph
from agent.analyst_agent import AnalystAgent
from agent.critic_agent import CriticAgent
from tools.pdf_tool import PDFTool
from typing import TypedDict, Annotated, List
from langchain_core.documents import Document
import operator


# 에이전트 인스턴스 생성
analyst_agent = AnalystAgent(name="AnalystAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
critic_agent = CriticAgent(name="CriticAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    fund_manager_agent = FundManagerAgent(name="FundManagerAgent", model_name="Qwen/Qwen2.5-0.5B", config={})

pdf_tool = PDFTool()


# State 정의
class GraphState(TypedDict):
    context: Annotated[List[Document], operator.add]
    answer: Annotated[List[Document], operator.add]
    question: Annotated[str, "user question"]
    sql_query: Annotated[str, "sql query"]
    binary_score: Annotated[str, "binary score yes or no"]
def analyst_agent_func(state:GraphState)->GraphState:
    # AnalystAgent 실행
    report = analyst_agent.run(
        ticker_list=state["context"],
        risk_preference=state["risk_preference"],
        lookback=state["lookback"],
        start_date=state["start_date"],
        end_date=state["end_date"],
        feedback=state["feedback"]
    )
    return {
        "context": report}
    
def critic_agent_func(state:GraphState)->GraphState:
    # CriticAgent 실행
    critic_report = critic_agent.run(analyst_report=state["context"])
    revised_analysis = critic_report[state["context"]].get("revised_analysis", "")
    if "수정" in revised_analysis:
        feedback = critic_report[state["context"]].get("critic", "")
        accepted = False
    else:
        accepted = True
    return {
        "context": critic_report,
        "feedback": feedback,
        "accepted": accepted
    }

def fundmanager_agent_func(state:GraphState)->GraphState:
    # FundManagerAgent 실행
    fund_manager_report = fund_manager_agent.run(critic_report=state["context"])
    return {
        "context": fund_manager_report
    }

workflow = StateGraph(GraphState)

workflow.add_state('analyst', analyst_agent_func)
workflow.add_state('critic', critic_agent_func)
workflow.add_state('fund_manager', 

#edge 연결
workflow.add_edge('analyst', 'critic')
workflow.add_edge('critic', 'fund_manager')

# 파라미터 설정
start_date = "2025-01-01"
end_date = "2025-01-30"
risk_preference = "공격적"
lookback = 200
max_iterations = 2

# 테스트용 티커 목록
ticker_list = ["AAPL", "TSLA", "GOOGL"]

# 부모 디렉토리 생성
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
parent_dir = os.path.join(os.getcwd(), f"run_{timestamp}")
os.makedirs(parent_dir, exist_ok=True)
stock_dir = os.path.join(parent_dir, "stock")
os.makedirs(stock_dir, exist_ok=True)
print(f"[INFO] Created parent directory: {parent_dir}")
print(f"[INFO] Created stock directory: {stock_dir}")

final_reports: Dict[str, dict] = {}

# 티커별 에이전트 루프 실행
for ticker in ticker_list:
    print(f"\n[INFO] Processing ticker: {ticker}")
    iteration = 0
    accepted = False
    feedback: Optional[str] = None
    report = None

    while iteration < max_iterations and not accepted:
        print(f"[DEBUG] Running AnalystAgent for ticker: {ticker}, Iteration: {iteration + 1}")
        
        # AnalystAgent 실행
        report = analyst_agent.run(
            ticker_list=[ticker],
            risk_preference=risk_preference,
            lookback=lookback,
            start_date=start_date,
            end_date=end_date,
            feedback=feedback
        )
        print(f"[INFO] Analyst report for {ticker}: {report}")

        # CriticAgent 실행
        critic_report = critic_agent.run(analyst_report=report)
        print(f"[INFO] Critic report for {ticker}: {critic_report}")
        
        revised_analysis = critic_report[ticker].get("revised_analysis", "")
        feedback = critic_report[ticker].get("critic", "") if "수정" in revised_analysis else None
        accepted = not feedback
        iteration += 1

        print(f"[DEBUG] Feedback for {ticker}: {feedback}")

    final_reports[ticker] = critic_report[ticker]

    # 각 티커의 critic pdf는 부모 디렉토리 아래 stock 디렉토리에 저장
    ticker_pdf_filename = os.path.join(stock_dir, f"{ticker}_critic_report.pdf")
    ticker_pdf = pdf_tool.run(
        report_data=critic_report[ticker]["critic"],
        filename=ticker_pdf_filename,
        report_type="critic"
    )
    print(f"[INFO] Critic Report PDF generated for {ticker}: {ticker_pdf}")

# 전체 리포트 JSON으로 저장
report_json_filename = os.path.join(parent_dir, "final_reports.json")
with open(report_json_filename, "w", encoding="utf-8") as f:
    json.dump(final_reports, f, ensure_ascii=False, indent=4)
print(f"[INFO] Saved final reports as JSON: {report_json_filename}")
