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
html_list = []


def get_ticker(start_date, end_date) -> list:
    db_client = analyst_agent.db_client
    cursor = db_client.cursor(dictionary=True)
    query = """
        SELECT DISTINCT ticker, stock_name
        FROM stock_reports
        WHERE date BETWEEN %s AND %s;
    """
    cursor.execute(query, (start_date, end_date))
    result = cursor.fetchall()
    cursor.close()
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
    print(f"[DEBUG] Iteration count: {state['iterate']}, Accepted: {state['accepted']}")  # 디버그 정보 출력
    
    if state['iterate'] > 3:  # 반복 횟수가 3 이상이면 무조건 종료
        print("[DEBUG] Maximum iteration reached. Ending process.")
        return "end"
    
    if state['accepted']:  # 승인된 경우 종료
        print("[DEBUG] Report accepted. Ending process.")
        return "end"
    
    if state['feedback'] is not None and not state['accepted']:  # 피드백이 있고, 아직 승인되지 않은 경우
        print("[DEBUG] Feedback provided but not accepted. Looping process.")
        return "loop"
    
    print("[DEBUG] No feedback or not accepted. Looping process.")
    return "loop"


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
        # state["accepted"] = False
    print(f"[INFO] Critic report for {state['ticker']}: {critic_report}")
    return state

def run(start_date, end_date, investment_tendency):
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

    # ===== 슬라이딩 윈도우 및 Lookback 파라미터 설정 =====
    # loop_start_date = datetime.date(2025, 2, 1)
    #2025-04-01
    loop_start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    # loop_end_date = datetime.date(2025, 3, 31)
    loop_end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    sliding_window_days = 3         # 슬라이딩 윈도우 기간: 7일
    lookback_period = 3             # lookback 기간: 7일
    risk_preference = investment_tendency
    # "나는 아주 공격적인 투자자야. 리스크를 매우 선호하고, 그만큼 고수익을 원해."

    # 전체 실행 결과 저장을 위한 부모 디렉토리 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    parent_dir = os.path.join(os.getcwd(), f"run_{timestamp}")
    os.makedirs(parent_dir, exist_ok=True)
    print(f"[INFO] Created parent directory: {parent_dir}")

    # ===== 슬라이딩 윈도우 루프 시작 =====
    current_date = loop_start_date
    while current_date <= loop_end_date:
        # 현재 윈도우의 시작일과 종료일 계산 (종료일은 7일간의 윈도우, 종료일이 루프 종료일을 넘지 않도록 조정)
        window_start = current_date
        window_end = current_date + datetime.timedelta(days=sliding_window_days - 1)
        if window_end > loop_end_date:
            window_end = loop_end_date

        start_date_str = window_start.strftime("%Y-%m-%d")
        end_date_str = window_end.strftime("%Y-%m-%d")
        print(f"\n[INFO] Processing window: {start_date_str} to {end_date_str}")

        # 현재 윈도우 전용 출력 디렉토리 생성
        window_dir = os.path.join(parent_dir, f"{start_date_str}_to_{end_date_str}")
        os.makedirs(window_dir, exist_ok=True)
        stock_dir = os.path.join(window_dir, "stock")
        os.makedirs(stock_dir, exist_ok=True)

        # 해당 기간의 티커 목록 조회
        tickers_data = get_ticker(start_date=start_date_str, end_date=end_date_str)
        ticker_list = sorted(pd.DataFrame(tickers_data)['ticker'].tolist()) if tickers_data else []
        
        # 각 티커별 최종 Critic 보고서를 저장할 딕셔너리
        final_reports: Dict[str, dict] = {}

        # 각 티커에 대해 analyst-critic 피드백 루프 실행
        for ticker in ticker_list:
            print(f"\n[INFO] Processing ticker: {ticker}")
            initial_state: GraphState = {
                "ticker": ticker,
                "context": {},
                "feedback": None,
                "risk_preference": risk_preference,
                "lookback": lookback_period,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "accepted": False,
                "iterate": 0
            }
            final_state = app.invoke(initial_state)
            final_reports[ticker] = final_state["context"]
            # 테스트를 위해 하나의 티커만 처리하고 싶다면 아래 break를 활성화하세요.
            break
        
        # 슬라이딩 윈도우별 FundManagerAgent 실행
        fund_manager_result = fund_manager_agent.run(final_reports, start_date_str, end_date_str)  
        print(f"[INFO] FundManagerAgent 최종 결과 for window {start_date_str} to {end_date_str}: {fund_manager_result}")
        # 각 티커별 Critic 보고서를 PDF로 생성
        
        for ticker, report_data in final_reports.items():
            analyst_report = report_data
            ticker_pdf_filename = os.path.join(stock_dir, f"{ticker}_critic_report.html")
            html_list.append(ticker_pdf_filename)
            critic_content = analyst_report.get("analysis", "최종 보고서")
            pdf_result = pdf_tool.run(
                report_data=critic_content,
                filename=ticker_pdf_filename,
            )
            print(f"[INFO] Report PDF generated for {ticker}: {pdf_result}")
        break

        # 윈도우 결과를 JSON 파일로 저장
        report_json = {
            "analyst_reports": final_reports,
            "fund_manager_result": fund_manager_result
        }
        report_json_filename = os.path.join(window_dir, "final_reports.json")
        with open(report_json_filename, "w", encoding="utf-8") as f:
            json.dump(report_json, f, ensure_ascii=False, indent=4)
        print(f"[INFO] Saved final reports as JSON: {report_json_filename}")

        # 각 윈도우별 티커 리스트를 CSV 파일로 저장 (end_date 이름의 폴더 생성)
        output_folder = os.path.join(window_dir, end_date_str)
        os.makedirs(output_folder, exist_ok=True)
        df = pd.DataFrame({'value': list(final_reports.keys())})
        df.index = [end_date_str] * len(final_reports)
        df.index.name = 'index'
        csv_file_path = os.path.join(output_folder, f"{end_date_str}.csv")
        df.to_csv(csv_file_path, index=True, encoding='utf-8-sig')
        print(f"[INFO] Saved CSV file: {csv_file_path}")

        # 다음 슬라이딩 윈도우로 이동
        current_date += datetime.timedelta(days=sliding_window_days)


    return html_list
