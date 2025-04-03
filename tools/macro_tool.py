import mysql.connector
from typing import Any, Optional
from config.config_loader import load_config

class MacroTool:
    """
    매크로 DB에서 지정된 날짜 범위 내의 최신 매크로 리포트를 가져온다.
    """
    def __init__(self, db_client: mysql.connector.connection.MySQLConnection):
        self.db_client = db_client

    def run(self, start_date: str, end_date: str) -> Optional[dict]:
        """
        start_date와 end_date 기준으로 매크로 리포트를 조회합니다.
        가장 최신의 리포트를 반환합니다.
        """
        query = """
            SELECT source, date, summary FROM macro_reports 
            WHERE date <= %s
            AND date >= %s
            ORDER BY date DESC 
            LIMIT 10;
        """
        cursor = self.db_client.cursor(dictionary=True)
        cursor.execute(query, (end_date, start_date))
        result = cursor.fetchall()
        cursor.close()
        return result

if __name__ == "__main__":
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
    macro_tool = MacroTool(db_client)
    start_date = "2025-03-21"
    end_date = "2025-03-28"
    
    macro_report = macro_tool.run(start_date, end_date)
    print("\n[Macro Report]")
    print(macro_report)
    
    db_client.close()
