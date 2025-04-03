import mysql.connector
from typing import Any, List
from config.config_loader import load_config

class StockTool:
    """
    특정 종목 리포트(DB1)에 대한 요약/검색/조회 기능.
    """
    def __init__(self, db_client: mysql.connector.connection.MySQLConnection):
        self.db_client = db_client

    def run(self, ticker: str, start_date: str, end_date: str) -> List[dict]:
        """
        ticker에 해당하는 모든 리포트를 조회합니다.
        
        Args:
            ticker (str): 조회할 종목 티커 (예: 'AAPL')
            start_date (str): 조회 시작 날짜 (예: '2025-01-01')
            end_date (str): 조회 종료 날짜 (예: '2025-02-20')
        
        Returns:
            List[dict]: 조회된 리포트의 목록
        """
        query = """
            SELECT ticker, stock_name, title, source, DATE_FORMAT(date, '%Y-%m-%d') AS date, summary FROM stock_reports 
            WHERE ticker = %s
            AND date BETWEEN %s AND %s
            ORDER BY date DESC;
            limit 5;
        """
        cursor = self.db_client.cursor(dictionary=True)
        cursor.execute(query, (ticker, start_date, end_date))
        results = cursor.fetchall()
        cursor.close()
        return results

if __name__ == '__main__':

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

    # MacroTool 사용 예시
    stock_tool = StockTool(db_client)

    # 하나 머티리얼즈가 예시
    ticker = '166090'
    start_date = "2025-01-01"
    end_date = "2025-02-20"
    
    stock_report = stock_tool.run(ticker, start_date, end_date)
    print("\n[Stock_Report]")
    print(stock_report)
    
    db_client.close()
