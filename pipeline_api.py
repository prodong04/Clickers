import os
import json
import pandas as pd
import httpx
import uvicorn
import asyncio
import sys
import datetime  # 시간 측정을 위한 모듈

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from tqdm import tqdm

from agent.analyst_agent import AnalystAgent
from agent.critic_agent import CriticAgent
from agent.fundmanager_agent import FundManagerAgent
from tools.pdf_tool import PDFTool

app = FastAPI()

# Request 모델 정의
class PipelineRequest(BaseModel):
    start_date: str = "2025-01-01"
    end_date: str = "2025-01-30"
    risk_preference: str = "공격적"
    lookback: int = 200
    max_iterations: int = 2

# 비동기 함수: 외부 URL에서 stock list(딕셔너리 리스트) 가져오기
async def fetch_stock_list(start_date: str, end_date: str) -> List[Dict]:
    url = "http://34.28.14.97:8000/stocks/reports"
    params = {"start_date": start_date, "end_date": end_date}
    print(f"[INFO] Fetching stock list from {url} with params: {params}")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        print(f"[DEBUG] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print("[ERROR] Failed to fetch stock list.")
            raise HTTPException(status_code=500, detail="Failed to fetch stock list")
        
        data = response.json()
        print(f"[DEBUG] Stock list data: {data}")
        
    return data

# 단순 함수: stock list에서 ticker 키를 추출하여 리스트 반환
async def get_ticker_list(start_date: str, end_date: str) -> List[str]:
    print(f"[INFO] Extracting ticker list for dates: {start_date} ~ {end_date}")
    start = datetime.datetime.now()
    data = await fetch_stock_list(start_date, end_date)
    ticker_list = [item["ticker"] for item in data if "ticker" in item]
    elapsed = (datetime.datetime.now() - start).total_seconds()
    print(f"[INFO] Ticker list extracted: {ticker_list} (소요시간: {elapsed:.2f}초)")
    return ticker_list

# 파이프라인 처리 함수 (순차 처리)
async def run_pipeline_logic(request: PipelineRequest) -> Dict:
    overall_start = datetime.datetime.now()
    print("[INFO] Starting pipeline execution")
    print(f"[DEBUG] PipelineRequest: {request}")
    
    # 부모 디렉토리(매 호출마다 새롭게 생성) 및 stock 서브디렉토리 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    parent_dir = os.path.join(os.getcwd(), f"run_{timestamp}")
    os.makedirs(parent_dir, exist_ok=True)
    stock_dir = os.path.join(parent_dir, "stock")
    os.makedirs(stock_dir, exist_ok=True)
    print(f"[INFO] Created parent directory: {parent_dir}")
    print(f"[INFO] Created stock directory: {stock_dir}")

    # 티커 목록 추출 (시간 측정)
    ticker_list = await get_ticker_list(request.start_date, request.end_date)
    print(f"[INFO] Received ticker list: {ticker_list}")

    if not ticker_list:
        print("[ERROR] No tickers found from stock list API.")
        raise HTTPException(status_code=404, detail="No tickers found from stock list API.")

    # 에이전트 및 PDFTool 인스턴스 생성
    analyst_agent = AnalystAgent(name="AnalystAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    critic_agent = CriticAgent(name="CriticAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    fund_manager_agent = FundManagerAgent(name="FundManagerAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    pdf_tool = PDFTool()

    final_reports: Dict[str, dict] = {}
    fund_manager_decisions: Dict[str, dict] = {}

    # 테스트를 위해 상위 3개 티커만 사용
    # ticker_list = ticker_list[:3]
    for ticker in tqdm(ticker_list, desc="Processing tickers"):
        ticker_start = datetime.datetime.now()
        print(f"\n[INFO] Processing ticker: {ticker}")
        iteration = 0
        accepted = False
        feedback: Optional[str] = None
        report = None

        # 티커별 에이전트 실행 (최대 max_iterations까지 반복)
        while iteration < request.max_iterations and not accepted:
            iter_start = datetime.datetime.now()
            print(f"[DEBUG] Running AnalystAgent for ticker: {ticker}, Iteration: {iteration + 1}")
            
            report = analyst_agent.run(
                ticker_list=[ticker],
                risk_preference=request.risk_preference,
                lookback=request.lookback,
                start_date=request.start_date,
                end_date=request.end_date,
                feedback=feedback
            )
            print(f"[INFO] Analyst report for {ticker}: {report}")

            critic_report = critic_agent.run(analyst_report=report)
            print(f"[INFO] Critic report for {ticker}: {critic_report}")
            
            revised_analysis = critic_report[ticker].get("revised_analysis", "")
            feedback = critic_report[ticker].get("critic", "") if "수정" in revised_analysis else None
            accepted = not feedback
            
            iter_elapsed = (datetime.datetime.now() - iter_start).total_seconds()
            print(f"[INFO] Iteration {iteration + 1} for ticker {ticker} took {iter_elapsed:.2f} seconds")
            print(f"[DEBUG] Feedback for {ticker}: {feedback}")
            iteration += 1

        final_reports[ticker] = critic_report[ticker]

        # 각 티커의 critic pdf는 부모 디렉토리 아래 stock 디렉토리에 저장
        ticker_pdf_filename = os.path.join(stock_dir, f"{ticker}_critic_report.pdf")
        ticker_pdf = pdf_tool.run(
            report_data=critic_report[ticker]["critic"],
            filename=ticker_pdf_filename,
            report_type="critic"
        )
        print(f"[INFO] Critic Report PDF generated for {ticker}: {ticker_pdf}")

        ticker_elapsed = (datetime.datetime.now() - ticker_start).total_seconds()
        print(f"[INFO] Total processing time for ticker {ticker}: {ticker_elapsed:.2f} seconds")

    # FundManagerAgent 실행 및 최종 결정 생성
    fm_start = datetime.datetime.now()
    fund_manager_decisions.update(fund_manager_agent.run(critic_report=final_reports))
    fm_elapsed = (datetime.datetime.now() - fm_start).total_seconds()
    print(f"[INFO] Fund Manager decisions: {fund_manager_decisions} (소요시간: {fm_elapsed:.2f}초)")

    # 최종 fundmanager pdf는 부모 디렉토리 바로 아래에 생성
    final_pdf_filename = os.path.join(parent_dir, "fund_manager_report.pdf")
    consolidated_pdf = pdf_tool.run(
        report_data=fund_manager_decisions,
        filename=final_pdf_filename,
        report_type="final"
    )
    print(f"[INFO] Consolidated Fund Manager PDF generated: {consolidated_pdf}")

    accepted_tickers = [
        ticker for ticker, decision in fund_manager_decisions.items() if decision.get("final_decision", False)
    ]
    df = pd.DataFrame({"ticker": accepted_tickers})
    # CSV 파일은 부모 디렉토리 바로 아래에 생성
    csv_filename = os.path.join(parent_dir, "accepted_tickers.csv")
    df.to_csv(csv_filename, index=False)
    print(f"[INFO] Accepted tickers CSV saved: {csv_filename}")

    overall_elapsed = (datetime.datetime.now() - overall_start).total_seconds()
    print(f"[INFO] Overall pipeline execution took {overall_elapsed:.2f} seconds")

    # PDF와 CSV 경로만 반환
    return {
        "status": "complete",
        "pdf_file": consolidated_pdf,
        "csv_file": csv_filename
    }

@app.post("/run_pipeline")
async def run_pipeline(request: PipelineRequest):
    try:
        result = await run_pipeline_logic(request)
        return JSONResponse(status_code=200, content={"status": "success", "result": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/custom_pdf")
async def custom_pdf():
    try:
        pdf_tool = PDFTool()
        # 부모 디렉터리 및 stocks 서브디렉터리 생성 (매 API 호출 시마다)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        parent_dir = os.path.join(os.getcwd(), f"run_{timestamp}")
        os.makedirs(parent_dir, exist_ok=True)
        stocks_dir = os.path.join(parent_dir, "stocks")
        os.makedirs(stocks_dir, exist_ok=True)
        print(f"[INFO] Created parent directory for custom_pdf: {parent_dir}")
        print(f"[INFO] Created stocks directory for custom_pdf: {stocks_dir}")

        # Dummy 종목 코드 (6자리 정수 문자열)
        dummy_tickers = ["006690", "012345", "000001"]

        # 각 종목별 dummy 리포트 PDF 생성 및 파일 경로 저장
        report_paths = {}
        for ticker in dummy_tickers:
            report_filename = os.path.join(stocks_dir, f"{ticker}_report.pdf")
            report_content = f"Dummy report for ticker {ticker}"
            generated_pdf = pdf_tool.run(
                report_data=report_content,
                filename=report_filename,
                report_type="report"
            )
            report_paths[ticker] = generated_pdf
            print(f"[INFO] Dummy report PDF generated for ticker {ticker}: {generated_pdf}")

        # 부모 디렉터리에 dummy fundmanager.pdf 생성
        fundmanager_pdf_filename = os.path.join(parent_dir, "fundmanager.pdf")
        fundmanager_content = "Dummy Fund Manager Report"
        generated_fundmanager_pdf = pdf_tool.run(
            report_data=fundmanager_content,
            filename=fundmanager_pdf_filename,
            report_type="final"
        )
        print(f"[INFO] Dummy Fund Manager PDF generated: {generated_fundmanager_pdf}")

        # CSV 파일 생성: 각 티커별 PDF 파일 경로 기록 (부모 디렉터리에 저장)
        csv_filename = os.path.join(parent_dir, "report_paths.csv")
        df = pd.DataFrame([{"ticker": ticker, "report_path": report_paths[ticker]} for ticker in dummy_tickers])
        df.to_csv(csv_filename, index=False)
        print(f"[INFO] CSV file with report paths saved: {csv_filename}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "complete",
                "pdf_file": generated_fundmanager_pdf,
                "csv_file": csv_filename
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 파일 다운로드 엔드포인트: 전달된 파일 경로에 따라 PDF 또는 CSV 파일을 반환
@app.get("/download_file")
async def download_file(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    _, ext = os.path.splitext(file_path)
    if ext.lower() == ".pdf":
        media_type = "application/pdf"
    elif ext.lower() == ".csv":
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=os.path.basename(file_path)
    )

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        uvicorn.run("pipeline_api:app", host="0.0.0.0", port=8000, reload=True)
    else:
        request = PipelineRequest()  # 기본값 사용
        result = asyncio.run(run_pipeline_logic(request))
        print("Pipeline execution result:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
