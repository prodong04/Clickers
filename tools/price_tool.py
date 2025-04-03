import os
import pandas as pd
import yfinance as yf
from typing import Any, Dict

from llm_manager import LLMManager  # 공유 LLM 매니저 임포트

class PriceTool:
    """
    가격 정보 조회 및 통계 계산 Tool
    """
    def __init__(self, name: str = "PriceTool", risk_free: str = "저는 공격적인 투자를 선호합니다"):
        self.name = name
        self.risk_free = risk_free
        self.device = 'cpu'
        self.chat_model = LLMManager.get_text_llm(model_name="solar-pro")

    def run(self, ticker: str, date: str, lookback: int = 200) -> Dict[str, Any]:
        """
        종목의 가격 데이터, 통계, 및 분석 결과를 텍스트로 반환합니다.
        """
        end_date = pd.to_datetime(date)
        start_date = end_date - pd.DateOffset(days=lookback)
        ticker = f"{ticker}.KS"

        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(interval='1d', start=start_date, end=end_date).ffill()

        kospi_ticker = yf.Ticker('^KS11')
        df_kospi = kospi_ticker.history(interval='1d', start=start_date, end=end_date).ffill()

        if df.empty:
            return {"message": f"{start_date.date()} ~ {end_date.date()} 기간 동안 {ticker}의 가격 데이터를 찾을 수 없습니다."}

        # 종가 및 거래량 데이터
        close_prices = df["Close"]
        volume = df["Volume"]
        pct_change = close_prices.pct_change()
        close_prices_mean = pct_change.mean()
        close_prices_std = pct_change.std()

        kospi_close_prices = df_kospi['Close']
        kospi_stat = kospi_close_prices.pct_change()
        kospi_mean = kospi_stat.mean()
        kospi_std = kospi_stat.std()

        # 가격 이동평균선 (5, 20, 60, 120일)
        ma_5 = close_prices.rolling(window=5).mean().iloc[-1]
        ma_20 = close_prices.rolling(window=20).mean().iloc[-1]
        ma_60 = close_prices.rolling(window=60).mean().iloc[-1]
        ma_120 = close_prices.rolling(window=120).mean().iloc[-1]

        # 가격 이동평균선 대비 현재가의 차이(디스패리티)
        disparity_ma5 = (close_prices.iloc[-1] - ma_5) / ma_5
        disparity_ma20 = (close_prices.iloc[-1] - ma_20) / ma_20
        disparity_ma60 = (close_prices.iloc[-1] - ma_60) / ma_60 if ma_60 else None
        disparity_ma120 = (close_prices.iloc[-1] - ma_120) / ma_120 if ma_120 else None

        # 거래량 이동평균선 (5, 20, 60, 120일)
        vol_ma_5 = volume.rolling(window=5).mean().iloc[-1]
        vol_ma_20 = volume.rolling(window=20).mean().iloc[-1]
        vol_ma_60 = volume.rolling(window=60).mean().iloc[-1]
        vol_ma_120 = volume.rolling(window=120).mean().iloc[-1]

        additional_info = {
            '사용자 위험 성향': self.risk_free,
            '디스패리티(5일)': disparity_ma5,
            '디스패리티(20일)': disparity_ma20,
            '디스패리티(60일)': disparity_ma60,
            '디스패리티(120일)': disparity_ma120,
            '종가 평균': close_prices_mean,
            '종가 표준편차': close_prices_std,
            'KOSPI 평균': kospi_mean,
            'KOSPI 표준편차': kospi_std,
            '평균 거래량': volume.mean(),
            '거래량 표준편차': volume.std()
        }

        # 텍스트로 LLM에 전달
        prompt = f"""
        당신은 월스트리트의 전문 트레이더입니다. 현재 주식의 성과를 분석하고 있습니다. 
        종목 코드: {ticker} ({lookback}일 동안의 데이터, 종료일: {date})
        사용자의 위험 성향은 다음과 같습니다: {self.risk_free}
        
        다음은 주식의 통계 정보입니다:

        📊 가격 분석 정보:
        - 디스패리티 (5일): {disparity_ma5:.4f}
        - 디스패리티 (20일): {disparity_ma20:.4f}
        - 디스패리티 (60일): {disparity_ma60 if disparity_ma60 else '데이터 없음'}
        - 디스패리티 (120일): {disparity_ma120 if disparity_ma120 else '데이터 없음'}
        - 종가 평균: {close_prices_mean:.4f}
        - 종가 표준편차: {close_prices_std:.4f}

        📊 KOSPI 비교 정보:
        - KOSPI 평균: {kospi_mean:.4f}
        - KOSPI 표준편차: {kospi_std:.4f}

        📊 거래량 정보:
        - 평균 거래량: {volume.mean():.2f}
        - 거래량 표준편차: {volume.std():.2f}

        위의 정보를 바탕으로 이 주식의 성과를 분석하고, 투자 기회를 평가해주세요. 
        또한, 사용자의 위험 성향을 고려하여 매수 또는 매도의 권장 사항을 제시해주세요.
        """

        response = self.chat_model(prompt=prompt, stream=False)

        return {
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            **additional_info,
            "llm_analysis": response
        }


if __name__ == '__main__':
    price_tool = PriceTool(name='PriceTool')
    date = '2024-12-31'
    ticker = '005930'
    lookback = 200

    result = price_tool.run(ticker, date, lookback)
    breakpoint()
    print(result)
