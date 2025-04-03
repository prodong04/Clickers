# main_fastapi.py
import os
import json
import pandas as pd
import httpx
import uvicorn
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    start_date: str = "2025-01-30"
    end_date: str = "2025-02-10"
    risk_preference: str = "공격적"
    lookback: int = 200
    max_iterations: int = 2

# 비동기 함수: 외부 URL에서 stock list(딕셔너리 리스트) 가져오기
async def fetch_stock_list(start_date: str, end_date: str) -> List[Dict]:
    url = "http://34.28.14.97:8000/stocks/reports"
    params = {"start_date": start_date, "end_date": end_date}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch stock list")
        data = response.json()
    return data

# 단순 함수: stock list에서 ticker 키를 추출하여 리스트 반환
async def get_ticker_list(start_date: str, end_date: str) -> List[str]:
    data = await fetch_stock_list(start_date, end_date)
    return [item["ticker"] for item in data if "ticker" in item]

# 파이프라인 처리 함수 (순차 처리)
async def run_pipeline_logic(request: PipelineRequest) -> Dict:
    ticker_list = await get_ticker_list(request.start_date, request.end_date)
    if not ticker_list:
        raise HTTPException(status_code=404, detail="No tickers found from stock list API.")

    # 에이전트 및 PDFTool 인스턴스 생성 (파라미터는 run() 호출 시 전달)
    analyst_agent = AnalystAgent(name="AnalystAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    critic_agent = CriticAgent(name="CriticAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    fund_manager_agent = FundManagerAgent(name="FundManagerAgent", model_name="Qwen/Qwen2.5-0.5B", config={})
    pdf_tool = PDFTool()

    final_reports: Dict[str, dict] = {}
    fund_manager_decisions: Dict[str, dict] = {}

    # 각 티커에 대해 순차적으로 처리 (GPU 메모리 문제로 병렬 처리 대신)
    for ticker in tqdm(ticker_list, desc="Processing tickers"):
        iteration = 0
        accepted = False
        feedback: Optional[str] = None
        report = None

        # Analyst & Critic 단계: 최대 max_iterations번 반복
        while iteration < request.max_iterations and not accepted:
            report = analyst_agent.run(
                ticker_list=[ticker],
                risk_preference=request.risk_preference,
                lookback=request.lookback,
                start_date=request.start_date,
                end_date=request.end_date,
                feedback=feedback
            )
            critic_report = critic_agent.run(analyst_report=report)
            revised_analysis = critic_report[ticker].get("revised_analysis", "")
            if "수정" in revised_analysis:
                feedback = critic_report[ticker].get("critic", "")
                accepted = False
            else:
                accepted = True
            iteration += 1

        final_reports[ticker] = critic_report[ticker]
        # 개별 Critic 리포트 PDF 생성 (마크다운 형식)
        ticker_pdf = pdf_tool.run(
            report_data=critic_report[ticker]["critic"],
            filename=f"{ticker}_critic_report.pdf",
            report_type="critic"
        )
        print(f"Critic Report PDF generated for ticker {ticker}: {ticker_pdf}")

    # FundManager 단계: 최종 결정을 내림
    fund_manager_decisions.update(fund_manager_agent.run(critic_report=final_reports))
    # 전체 FundManager 리포트 PDF 생성
    consolidated_pdf = pdf_tool.run(
        report_data=fund_manager_decisions,
        filename="fund_manager_report.pdf",
        report_type="final"
    )
    print(f"Consolidated Fund Manager PDF generated: {consolidated_pdf}")

    # 최종 편입된 티커 CSV 생성
    accepted_tickers = [
        ticker for ticker, decision in fund_manager_decisions.items() if decision.get("final_decision", False)
    ]
    df = pd.DataFrame({"ticker": accepted_tickers})
    csv_filename = "accepted_tickers.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Accepted tickers CSV saved: {csv_filename}")

    # 생성된 PDF와 CSV 파일을 ZIP 파일로 묶음
    zip_filename = "pipeline_result.zip"
    with zipfile.ZipFile(zip_filename, "w") as zipf:
        zipf.write(consolidated_pdf)
        zipf.write(csv_filename)
    print(f"Pipeline result ZIP generated: {zip_filename}")

    return {
        "zip_file": zip_filename,
        "final_decisions": fund_manager_decisions
    }

@app.post("/run_pipeline")
async def run_pipeline(request: PipelineRequest):
    try:
        result = await run_pipeline_logic(request)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# /custom_pdf 엔드포인트: 임의의 커스텀 PDF와 CSV 파일을 ZIP 파일로 묶어 반환
@app.get("/custom_pdf")
async def custom_pdf():
    try:
        pdf_tool = PDFTool()
        # 임의의 커스텀 PDF 생성
        custom_pdf_path = pdf_tool.run(
            report_data="## Custom PDF Report\nThis is a custom report generated for testing purposes.",
            filename="custom_report.pdf",
            report_type="critic"
        )
        # 임의의 커스텀 CSV 생성
        custom_csv_path = "custom_data.csv"
        df = pd.DataFrame({
            "Column1": ["Value1", "Value2"],
            "Column2": [123, 456]
        })
        df.to_csv(custom_csv_path, index=False)

        # 두 파일을 ZIP 파일로 묶음
        zip_filename = "custom_files.zip"
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            zipf.write(custom_pdf_path)
            zipf.write(custom_csv_path)

        return FileResponse(
            path=zip_filename,
            media_type="application/zip",
            filename=zip_filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
