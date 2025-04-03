# tools/financial_tool.py
from typing import Any, Optional
import pandas as pd
import json
from datetime import datetime
import pymysql
import OpenDartReader
import logging
from pykrx import stock
from llm_manager import LLMManager  # 공유 LLM 매니저 임포트


logger = logging.getLogger('financial_tool')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Dart API 설정
api_key = '1de1e50669f96282a58dd16a61ddc9acf7d84971'
if api_key is None:
    logger.error("Dart API 키가 필요합니다.")
    raise ValueError("Dart API 키가 필요합니다.")

dart = OpenDartReader(api_key)

# 분기별 보고서 정보: (분기, 보고서 코드, 발표월, 발표일)
REPORT_INFO = [
    ("4Q", "11011", 3, 18),   
    ("3Q", "11014", 11, 14),  
    ("2Q", "11012", 8, 14),   
    ("1Q", "11013", 5, 15)    
]

def get_publish_date(year: int, quarter: str) -> datetime:
    """
    time에 해당하는 발표일을 datetime 객체로 반환
    """
    if quarter == "4Q":
        return datetime(year+1, 3, 18)
    elif quarter == "3Q":
        return datetime(year, 11, 14)
    elif quarter == "2Q":
        return datetime(year, 8, 14)
    else:  
        return datetime(year, 5, 15)

def get_previous_quarter(year: int, quarter: str):
    """
    현재 분기 (year, quarter)에서 바로 이전 분기를 반환 -> 이전 분기 (year, quarter)
    1분기의 경우 연도가 -1 되는 로직 포함
    """
    q_list = ["4Q", "3Q", "2Q", "1Q"]
    idx = q_list.index(quarter)
    new_idx = (idx + 1) % 4  
    new_q = q_list[new_idx]
    new_year = year if not (quarter == '1Q') else (year - 1)
    return (new_year, new_q)

def find_latest_published_quarter(base_date: datetime):
    """
    base_date 기준으로 '이미 발표된' 분기 중 가장 최신 분기(year, quarter, report_code)를 찾는다.
    """
    check_year = base_date.year
    while True:
        for (q, code, _, _) in REPORT_INFO:
            pub_date = get_publish_date(check_year, q)
            if pub_date <= base_date:
                return (check_year, q, code)
        check_year -= 1

def get_recent_three_reports(base_date: datetime):
    """
    base_date 기준으로 이미 발표된 보고서 중 가장 최신(#1) + 바로 이전(#2, #3)을 찾아 반환
    """
    y, q, code = find_latest_published_quarter(base_date)
    pub_date = get_publish_date(y, q)
    
    results = [{
        "label": "#1",
        "year": y,
        "quarter": q,
        "report_code": code,
        "publish_date": pub_date
    }]
    
    prev_year, prev_q = y, q
    for i in range(2):
        prev_year, prev_q = get_previous_quarter(prev_year, prev_q)
        for item in REPORT_INFO:
            if item[0] == prev_q:
                prev_code = item[1]
        p_date = get_publish_date(prev_year, prev_q)
        results.append({
            "label": f"#{i+2}",
            "year": prev_year,
            "quarter": prev_q,
            "report_code": prev_code,
            "publish_date": p_date
        })
    
    return results

def fetch_dart_finstate(company: str, year: int, report_code: str) -> pd.DataFrame:
    """
    OpenDartReader finstate로 재무제표 조회
    """
    df = dart.finstate(company, year, reprt_code=report_code)
    if df is None or df.empty:
        return pd.DataFrame()
    
    df = df.rename(
        columns={
            'account_nm': '계정명',
            'fs_div': '개별/연결',
            'thstrm_amount': '금액',
        }
    )
    
    def to_float(x):
        try:
            return float(str(x).replace(',', '')) / 100000000 
        except:
            return 0.0
    df['금액'] = df['금액'].apply(to_float)
    return df[['계정명', '개별/연결', '금액']]

def calculate_qoq_change(prev, curr):
    """
    QoQ 변동률 계산
    """
    if prev == 0 or prev is None:
        return None
    change = round(((curr - prev) / prev) * 100, 1)
    sign = "+" if change > 0 else ""
    return f"{sign}{change}%"

class FinancialTool:
    """
    재무제표 조회(DB4)
    """
    def __init__(self):
        """
        인스턴스 생성 시 아무 인자도 받지 않음
        """
        self.chat_model = LLMManager.get_text_llm(model_name="solar-pro")   

    def generate_summary(self):
        logger.info(f"[기준일: {self.base_date.strftime('%Y-%m-%d')}] {self.company_name}({self.ticker})의 최근 3개 보고서를 확인합니다.")
        for report in self.reports:
            logger.info(f" {report['label']}: {report['year']}년 {report['quarter']} "
                        f"(공시={report['publish_date'].strftime('%Y-%m-%d')}, code={report['report_code']})")
        
        dfs = {}
        for report in self.reports:
            df = fetch_dart_finstate(self.ticker, report['year'], report['report_code'])
            if not df.empty:
                dfs[report['label']] = df
            else:
                print(f"{report['year']}년도 {report['quarter']}분기의 재무제표 데이터가 없습니다.")
        
        target_cols = ['당기순이익', '영업이익', '매출액']
        for i in range(1, len(self.reports)):
            curr_label, prev_label = self.reports[i-1]['label'], self.reports[i]['label']
            prev_df, curr_df = dfs[prev_label], dfs[curr_label]
            if '1' in self.reports[i-1]['quarter']:
                continue
            for col in target_cols:
                prev_val = prev_df.loc[prev_df['계정명'] == col, '금액'].values[0] if col in prev_df['계정명'].values else 0
                curr_val = curr_df.loc[curr_df['계정명'] == col, '금액'].values[0] if col in curr_df['계정명'].values else 0
                dfs[curr_label].loc[dfs[curr_label]['계정명'] == col, '금액'] = curr_val - prev_val
        
        all_cols = ["당기순이익", "영업이익", "매출액", "부채총계", "비유동부채", "유동부채", "자산총계", "자본총계"]
        financial_data = {}
        
        prev_label, curr_label = self.reports[1]['label'], self.reports[0]['label']
        prev_df, curr_df = dfs[prev_label], dfs[curr_label]
        
        for col in all_cols:
            prev_val = prev_df.loc[
                (prev_df['계정명'] == col) & (prev_df['개별/연결'] == 'CFS'), '금액'
            ].values[0] if not prev_df.loc[
                (prev_df['계정명'] == col) & (prev_df['개별/연결'] == 'CFS'), '금액'
            ].empty else prev_df.loc[
                (prev_df['계정명'] == col) & (prev_df['개별/연결'] == 'OFS'), '금액'
            ].values[0] if not prev_df.loc[
                (prev_df['계정명'] == col) & (prev_df['개별/연결'] == 'OFS'), '금액'
            ].empty else 0

            curr_val = curr_df.loc[
                (curr_df['계정명'] == col) & (curr_df['개별/연결'] == 'CFS'), '금액'
            ].values[0] if not curr_df.loc[
                (curr_df['계정명'] == col) & (curr_df['개별/연결'] == 'CFS'), '금액'
            ].empty else curr_df.loc[
                (curr_df['계정명'] == col) & (curr_df['개별/연결'] == 'OFS'), '금액'
            ].values[0] if not curr_df.loc[
                (curr_df['계정명'] == col) & (curr_df['개별/연결'] == 'OFS'), '금액'
            ].empty else 0

            qoq_change = calculate_qoq_change(prev_val, curr_val)

            if col not in financial_data:
                financial_data[col] = {}
            save_name_prev = f"{self.reports[1]['year']}년 {self.reports[1]['quarter']} "
            save_name_curr = f"{self.reports[0]['year']}년 {self.reports[0]['quarter']} "
            financial_data[col][save_name_prev] = f"{round(prev_val, 2)}억 원"
            financial_data[col][save_name_curr] = f"{round(curr_val, 2)}억 원"
            financial_data[col]["QoQ Change"] = qoq_change

        title = f"{self.company_name}의 {save_name_curr} 재무제표 분석"
        output_json = {
            "제목": title,
            "profitability": {
                "당기순이익": financial_data["당기순이익"],
                "영업이익": financial_data["영업이익"]
            },
            "revenue_growth": {
                "매출액": financial_data["매출액"]
            },
            "debt_levels": {
                "부채총계": financial_data["부채총계"],
                "비유동부채": financial_data["비유동부채"],
                "유동부채": financial_data["유동부채"]
            },
            "assets_and_equity": {
                "자산총계": financial_data["자산총계"],
                "자본총계": financial_data["자본총계"]
            }
        }

        processed_data = json.dumps(output_json, indent=4, ensure_ascii=False)
        print(processed_data)
        
        example_data = {
            "Profitability": "애플의 순이익은 2023년 2분기 198.8억 달러에서 2023년 3분기 229.6억 달러로 증가하여 강한 수익성을 나타냅니다. 같은 기간 동안 총이익도 364.1억 달러에서 404.3억 달러로 증가했습니다.",
            "Revenue Growth": "총 매출은 2023년 2분기 818.0억 달러에서 2023년 3분기 895.0억 달러로 증가하여 긍정적인 매출 성장을 보였습니다.",
            "Debt Levels": "회사의 총 부채는 2023년 2분기 2,747.6억 달러에서 2023년 3분기 2,904억 달러로 증가했습니다. 장기 부채는 980.7억 달러에서 952.8억 달러로 감소했지만, 단기 부채는 112.1억 달러에서 158.1억 달러로 증가했습니다. 순부채도 808.7억 달러에서 811.2억 달러로 소폭 증가했습니다. 이는 회사의 부채 수준이 증가하고 있음을 나타내며, 적절히 관리되지 않으면 우려 요인이 될 수 있습니다.",
            "Assets and Equity": "총자산은 2023년 2분기 3,350.4억 달러에서 2023년 3분기 3,525.8억 달러로 증가했습니다. 총 주주 자본도 602.7억 달러에서 621.5억 달러로 증가하여 회사의 자산과 자본이 성장하고 있음을 보여줍니다.",
            "Conclusion": "애플은 강한 수익성과 매출 성장을 보여줍니다. 그러나 증가하는 부채 수준은 면밀히 모니터링해야 합니다. 회사는 긍정적인 현금 흐름을 생성하고 있으며, 자산과 자본이 증가하고 있습니다."
        }

        prompt = f"""
        Example:
        {json.dumps(example_data, indent=4, ensure_ascii=False)}

        Financial Data:
        {processed_data}
        """
        prompt = """
                You are a financial analyst. 
                Based on the following financial data, generate a fundamental summary in a structured format similar to the example provided.
                """
        response = self.chat_model(prompt=prompt, stream=False)
        return response

    def run(self, ticker: str, time: Optional[str] = None):
        """
        ticker: 조회할 종목 이름
        time: 조회할 시간 ("YYYY-MM-DD" 형식으로 입력, None이면 현재 시간 기준)
        """
        self.ticker = ticker
        self.company_name = stock.get_market_ticker_name(ticker)
        
        if time is None:
            self.base_date = datetime.today()
        else:
            self.base_date = datetime.strptime(time, "%Y-%m-%d")
        
        self.reports = get_recent_three_reports(self.base_date)
        
        
        summary = self.generate_summary()
        summary_text = json.dumps(summary, ensure_ascii=False)
        file_name = f"{self.company_name}_{self.reports[0]['year']}년_{self.reports[0]['quarter']}분기_재무제표"
        return summary_text, file_name
        
        

# 사용 예시
if __name__ == "__main__":
    tool = FinancialTool()
    tool.run(ticker="001040", time="2024-12-20")