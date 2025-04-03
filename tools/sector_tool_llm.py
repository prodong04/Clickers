import os
import re
from openai import OpenAI  # openai==1.52.2 이상 버전 필요
import datetime  # 전체 datetime 모듈을 import로 변경
from typing import List
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

class SectorTool:
    """
    MySQL에서 종목 summary를 가져와 그 텍스트를 쿼리로 사용하여,
    MongoDB Atlas Vector Search 인덱스를 통해 관련 섹터 문서의 summary를 Top-K로 리트리버합니다.
    
    인스턴스 생성 시, MYSQL_URL, MONGO_URL, UPSTAGE_API_KEY를 인자로 받아 사용하며,
    환경변수에 값이 없으면 .env에 저장된 값을 사용합니다.
    """
    def __init__(self, mysql_url: str = None, mongo_url: str = None, upstage_api_key: str = None):

        # Upstage 클라이언트 초기화 (인스턴스 변수로 저장)
        self.client = OpenAI(
            api_key=upstage_api_key,
            base_url="https://api.upstage.ai/v1"
        )

        # 1) MySQL 연결 설정
        self.mysql_engine = self.create_mysql_engine(mysql_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.mysql_engine)

        # 2) MongoDB Atlas 연결
        self.mongo_client = self.create_mongo_client(mongo_url)
        # 데이터베이스와 컬렉션은 환경변수에 저장된 값 또는 기본값 사용
        self.database = self.mongo_client[os.environ.get("MONGO_DB", "alpha-agent")]
        self.collection = self.database[os.environ.get("MONGO_COLLECTION", "sector-embedding")]


    def get_stock_summary(self, ticker: str) -> str:
        """
        MySQL의 stock_reports 테이블에서 ticker에 해당하는 종목 summary를 조회하고,
        '종목 키워드'와 '종목 설명' 부분만 추출하여 반환합니다.
        
        Args:
            ticker (str): 조회할 종목의 티커 (예: "166090").
        
        Returns:
            str: 추출된 종목 키워드와 종목 설명이 결합된 문자열. 조회 실패 시 빈 문자열 반환.
        """
        query = text("""
            SELECT keyword
            FROM stock_reports
            WHERE ticker = :ticker
            LIMIT 1
        """)
        with self.mysql_engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker}).fetchone()

        if result and result[0]:
            summary = result[0]
            # "종목 키워드:" 이후부터 \ 또는 줄바꿈 전까지 추출 (공백 제거)
            keyword_pattern = r"종목 키워드:\s*(.*?)(?:\\|\n)"
            m_keyword = re.search(keyword_pattern, summary)
            keyword_text = m_keyword.group(1).strip() if m_keyword else ""

            # "종목 설명:" 또는 "1. 종목 설명:" 이후부터 \ 또는 줄바꿈 전까지 추출
            description_pattern = r"(?:\d+\.\s*)?종목 설명:\s*(.*?)(?:\\|\n)"
            m_desc = re.search(description_pattern, summary)
            description_text = m_desc.group(1).strip() if m_desc else ""

            return f"{keyword_text}\n\n{description_text}"
        else:
            return ""

    
    @staticmethod
    def create_mysql_engine(mysql_url: str):
        """
        환경변수에 저장된 MYSQL_URL 또는 인자로 전달된 URL을 사용하여 MySQL 데이터베이스 엔진을 생성합니다.
        
        Args:
            mysql_url (str): MySQL 연결 URL.
        
        Returns:
            Engine: SQLAlchemy의 MySQL 데이터베이스 엔진 객체.
        """
        return create_engine(mysql_url, echo=False)

    @staticmethod
    def create_mongo_client(mongo_url: str):
        """
        환경변수에 저장된 MONGO_URL 또는 인자로 전달된 URL을 사용하여 MongoDB 클라이언트를 생성합니다.
        
        Args:
            mongo_url (str): MongoDB 연결 URL.
        
        Returns:
            MongoClient: PyMongo MongoDB 클라이언트 객체.
        """
        return MongoClient(mongo_url, server_api=ServerApi('1'))

    def retrieve_related_sector_reports_with_llm(self, ticker: str, top_k: int = 5, days_ago: int = 14) -> List[int]:
        """
        LLM을 활용하여 특정 종목과 관련성 높은 섹터 리포트를 찾습니다.
        최근 days_ago일 이내의 데이터만 검색합니다.
        
        Args:
            ticker (str): 조회할 종목의 티커 (예: "166090").
            top_k (int, optional): 반환할 섹터 리포트의 최대 개수. 기본값은 5.
            days_ago (int, optional): 현재로부터 최근 몇일 전 데이터부터 검색할지. 기본값은 14일(2주).
        
        Returns:
            List[int]: 관련성 높은 섹터 리포트의 MySQL ID 목록.
        """
        stock_summary = self.get_stock_summary(ticker)
        if not stock_summary:
            print("MySQL에 해당 종목 summary가 없습니다.")
            return []
        
        stock_name = self.get_stock_name(ticker)
        if not stock_name:
            stock_name = f"티커 {ticker} 종목"
        
        # 3. MySQL에서 최근 days_ago일 이내의 섹터 리포트 가져오기
        sector_reports = self.get_recent_sector_reports(days_ago)
        if not sector_reports:
            print(f"최근 {days_ago}일 내에 생성된 섹터 리포트가 없습니다.")
            return []
        
        print(f"{len(sector_reports)}개의 섹터 리포트를 분석합니다...")
        
        # 4. 배치 처리 개선
        related_report_ids = []
        batch_size = 10
        total_reports = min(len(sector_reports), 1000)  # 최대 100개 처리
        total_batches = (total_reports + batch_size - 1) // batch_size
        
        # 배치를 다양하게 구성하기 위해 리포트 섞기
        import random
        shuffled_indices = list(range(total_reports))
        random.shuffle(shuffled_indices)
        
        for batch_idx in range(total_batches):
            # 배치 인덱스 계산
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_reports)
            batch_indices = shuffled_indices[start_idx:end_idx]
            
            # 각 배치마다 다양한 리포트 포함
            batch_reports = [sector_reports[i] for i in batch_indices]
            
            # 각 리포트의 ID를 명확히 추적
            id_mapping = {i: sector_reports[batch_indices[i]]["id"] for i in range(len(batch_reports))}
            
            # LLM 프롬프트 구성 (ID 매핑 정보 포함)
            prompt = self.create_relevance_prompt(stock_name, stock_summary, batch_reports, id_mapping)
            
            try:
                # LLM 호출
                response = self.client.chat.completions.create(
                    model="solar-pro-241126",
                    messages=[
                        {"role": "system", "content": "당신은 금융 전문가입니다. 주식 종목과 섹터 리포트 간의 관련성을 판단하는 작업을 수행합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                
                # 응답 파싱
                result = response.choices[0].message.content
                print(f"배치 {batch_idx+1}/{total_batches} LLM 응답:", result[:100], "...")
                
                # 반환된 인덱스를 실제 리포트 ID로 변환
                report_indices = self.parse_llm_batch_response(result)
                report_ids = [id_mapping[idx] for idx in report_indices if idx in id_mapping]
                
                # 결과에 추가
                for report_id in report_ids:
                    if report_id not in related_report_ids:  # 중복 제거
                        related_report_ids.append(report_id)

                print(f"배치 {batch_idx+1}/{total_batches} 처리 완료, 현재까지 {len(related_report_ids)}개 관련 리포트 ID 발견")
                
            except Exception as e:
                print(f"LLM 호출 중 오류 발생: {e}")
        
        # 5. 상위 K개 반환
        return related_report_ids[:top_k]
    
    # def retrieve_related_sector_reports_with_llm(self, ticker: str, top_k: int = 5, days_ago: int = 14) -> List[int]:
    #     """
    #     LLM을 활용하여 특정 종목과 관련성 높은 섹터 리포트를 찾습니다.
    #     최근 days_ago일 이내의 데이터만 검색합니다.
        
    #     Args:
    #         ticker (str): 조회할 종목의 티커 (예: "166090").
    #         top_k (int, optional): 반환할 섹터 리포트의 최대 개수. 기본값은 5.
    #         days_ago (int, optional): 현재로부터 최근 몇일 전 데이터부터 검색할지. 기본값은 14일(2주).
        
    #     Returns:
    #         List[int]: 관련성 높은 섹터 리포트의 MySQL ID 목록.
    #     """
    #     # 1. 종목 정보 가져오기
    #     stock_summary = self.get_stock_summary(ticker)
    #     if not stock_summary:
    #         print("MySQL에 해당 종목 summary가 없습니다.")
    #         return []
        
    #     # 2. 종목 이름 가져오기
    #     stock_name = self.get_stock_name(ticker)
    #     if not stock_name:
    #         stock_name = f"티커 {ticker} 종목"
        
    #     # 3. MySQL에서 최근 days_ago일 이내의 섹터 리포트 가져오기
    #     sector_reports = self.get_recent_sector_reports(days_ago)
    #     if not sector_reports:
    #         print(f"최근 {days_ago}일 내에 생성된 섹터 리포트가 없습니다.")
    #         return []
        
    #     print(f"{len(sector_reports)}개의 섹터 리포트를 분석합니다...")
        
    #     max_reports = 100  # 한 번에 처리할 수 있는 최대 리포트 수
    #     if len(sector_reports) > max_reports:
    #         # 최신 데이터 우선 선택
    #         sector_reports = sector_reports[:max_reports]
    #         print(f"처리 가능한 최대 {max_reports}개의 최신 리포트만 분석합니다.")

    #     # LLM 프롬프트 구성
    #     prompt = self.create_relevance_prompt(stock_name, stock_summary, sector_reports)
        
    #     try:
    #         # LLM 호출 (한 번만 호출)
    #         response = self.client.chat.completions.create(
    #             model="solar-pro-241126",
    #             messages=[
    #                 {"role": "system", "content": "당신은 금융 전문가입니다. 주식 종목과 섹터 리포트 간의 관련성을 판단하는 작업을 수행합니다."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             temperature=0.2
    #         )
            
    #         # 응답 파싱
    #         result = response.choices[0].message.content
    #         related_report_ids = self.parse_llm_response(result)
            
    #         # 상위 K개만 반환
    #         return related_report_ids[:top_k]
            
    #     except Exception as e:
    #         print(f"LLM 호출 중 오류 발생: {e}")
    #         return []

    def get_stock_name(self, ticker: str) -> str:
        """
        MySQL의 stock_reports 테이블에서 ticker에 해당하는 종목명을 조회합니다.
        
        Args:
            ticker (str): 조회할 종목의 티커 (예: "166090").
        
        Returns:
            str: 종목명. 조회 실패 시 빈 문자열 반환.
        """
        query = text("""
            SELECT stock_name
            FROM stock_reports
            WHERE ticker = :ticker
            LIMIT 1
        """)
        with self.mysql_engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker}).fetchone()

        return result[0] if result else ""

    def get_recent_sector_reports(self, days_ago: int = 14) -> List[dict]:
        """
        MySQL의 sector_reports 테이블에서 최근 days_ago일 이내의 섹터 리포트를 가져옵니다.
        
        Args:
            days_ago (int): 현재로부터 몇 일 전까지의 데이터를 가져올지 지정. 기본값은 14일(2주).
            
        Returns:
            List[dict]: 섹터 리포트 딕셔너리 목록.
        """
        # 현재 날짜에서 days_ago일 전 날짜 계산
        from_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        from_date_str = from_date.strftime("%Y-%m-%d")
        
        query = text(f"""
            SELECT id, date, title, summary, source, keyword
            FROM sector_reports
            WHERE keyword IS NOT NULL 
            AND keyword != ''
            AND date >= '{from_date_str}'
            ORDER BY date DESC
        """)
        
        try:
            with self.mysql_engine.connect() as conn:
                results = conn.execute(query).fetchall()
                
            print(f"최근 {days_ago}일 내의 섹터 리포트 {len(results)}개를 가져왔습니다.")
            
            sector_reports = []
            for row in results:
                # datetime.date를 datetime.datetime으로 변환
                date_value = row[1]
                if isinstance(date_value, datetime.date) and not isinstance(date_value, datetime.datetime):
                    date_value = datetime.datetime.combine(date_value, datetime.time.min)
                    
                sector_reports.append({
                    "id": row[0],
                    "date": date_value,
                    "title": row[2],
                    "summary": row[3],
                    "source": row[4],
                    "keyword": row[5]
                })
            
            return sector_reports
        except Exception as e:
            print(f"최근 섹터 리포트 조회 중 오류 발생: {e}")
            return []

    def create_relevance_prompt(self, stock_name: str, stock_summary: str, batch_reports: List[dict], id_mapping: dict) -> str:
        """
        종목과 섹터 리포트 간의 관련성을 판단하기 위한 LLM 프롬프트를 생성합니다.
        """
        prompt = f"""Find sector reports that are highly relevant to the stock '{stock_name}'.

        Stock Information:
        {stock_summary}

        Your mission is to accurately determine the relevance between the above stock and the sector reports listed below. Evaluate relevance based on the following criteria:

        서로 겹치는 단어가 많다면 무조건 뽑아.

        IMPORTANT: Do NOT include any reports that are definitely unrelated to the stock. Exclude any report where you cannot establish a clear and direct connection. Never include reports with tenuous or speculative connections - only include reports with concrete, meaningful relevance to the stock.
        
        Here is the list of sector reports:
        """
        
        for i, report in enumerate(batch_reports):
            # prompt += f"\n[ID: {report['id']}] Title: {report['title']}\n"
            prompt += f"Content: {report['keyword'][:250]}\n"
            # prompt += f"Source: {report['source']}\n"
            prompt += "---\n"
        
        prompt += """
        List ONLY the index numbers (not IDs) of relevant reports in JSON format:
        ```json
        {
        "relevant_indices": [index1, index2, ...]
        }
        ```
        """
        
        # print(prompt)
        return prompt

    def parse_llm_batch_response(self, llm_response: str) -> List[int]:
        """배치 응답에서 인덱스 번호 추출"""
        try:
            import json
            import re
            
            json_pattern = r'\{.*"relevant_indices"\s*:\s*\[.*\].*\}'
            match = re.search(json_pattern, llm_response)
            
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                return data.get("relevant_indices", [])
            
            # 백업 방법: 단순 숫자 추출
            numbers = re.findall(r'\b\d+\b', llm_response)
            return [int(num) for num in numbers if int(num) < 10]  # 배치 인덱스는 0-9 범위
        
        except Exception as e:
            print(f"배치 응답 파싱 오류: {e}")
            return []
        
    def create_final_selection_prompt(self, stock_name: str, stock_summary: str, candidate_reports: List[dict], top_k: int) -> str:
        """최종 선택을 위한 프롬프트를 구성합니다. 
        상세 내용과 요약 정보를 모두 포함하여 더 정확한 판단이 가능하게 합니다.
        """
        prompt = f"""Among these pre-selected sector reports, choose the TOP {top_k} reports that are MOST relevant and valuable to investors interested in '{stock_name}'.

    STOCK INFORMATION:
    {stock_summary}

    CANDIDATE REPORTS:
    """
        
        for i, report in enumerate(candidate_reports):
            # 상세 정보 포함
            prompt += f"\n[ID: {report['id']}] {report['title']}\n"
            prompt += f"Date: {report['date']}\n"
            prompt += f"Source: {report['source']}\n"
            # 요약은 길 수 있으므로 일부만 포함
            # summary_excerpt = report['summary'] + "..." if len(report['summary']) > 300 else report['summary']
            prompt += f"Summary: {report['summary']}\n"
            prompt += f"Keywords: {report['keyword']}\n"
            prompt += "---\n"
        
        prompt += f"""
        INSTRUCTIONS:
        0. 종목 이름이 섹터 리포트에 등장하면 무조건 뽑아.
        1. Analyze each report's relevance to {stock_name}'s business, industry, and market position
        2. Consider recent developments, competitive landscape, and supply chain implications
        3. Prioritize reports with direct impact on stock valuation or business prospects
        4. Select EXACTLY {top_k} most relevant reports (no more, no less)

        RESPONSE FORMAT:
        Return a JSON object with your final selection:
        ```json
        {{
        "selection": [ID1, ID2, ..., ID{top_k}],
        "reasoning": "Brief explanation of your selection criteria and why these reports are most valuable"
        }} """

        return prompt
   
    def parse_final_selection_response(self, llm_response:str) -> List[int]:
        """
        최종 선택 응답에서 선택된 리포트 ID 목록을 추출합니다. 
        """
        try: 
            import json 
            import re
            # JSON 패턴 찾기
            json_pattern = r'\{.*"selection"\s*:\s*\[.*\].*\}'
            match = re.search(json_pattern, llm_response)
            
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                return data.get("selection", [])
            
            # 백업 패턴: 단순 숫자 배열 추출
            array_pattern = r'\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]'
            match = re.search(array_pattern, llm_response)
            if match:
                numbers_str = match.group(1)
                return [int(num.strip()) for num in numbers_str.split(',')]
                
            # 최후 백업: 일반 숫자 추출
            numbers = re.findall(r'\b\d+\b', llm_response)
            return [int(num) for num in numbers]
            
        except Exception as e:
            print(f"최종 선택 응답 파싱 오류: {e}")
            return []



    def refine_report_selection(self, ticker: str, candidate_reports: List[dict], top_k: int) -> List[dict]:
        """
        1단계에서 선정된 후보 리포트들을 더 세밀하게 분석하여 최종 top_k개를 선정합니다.
        """
        # 종목 정보 및 이름 가져오기
        stock_summary = self.get_stock_summary(ticker)
        stock_name = self.get_stock_name(ticker) or f"티커 {ticker} 종목"
        
        # 2단계 프롬프트 구성 (상세 정보 포함)
        prompt = self.create_final_selection_prompt(stock_name, stock_summary, candidate_reports, top_k)
        
        try:
            # LLM 호출
            response = self.client.chat.completions.create(
                model="solar-pro-241126",
                messages=[
                    {"role": "system", "content": "당신은 금융 애널리스트로서, 최종 선택된 섹터 리포트가 투자 의사결정에 중요한 영향을 미칩니다. 가장 관련성 높고 가치 있는 정보만 선별하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # 응답 파싱
            result = response.choices[0].message.content
            print("최종 선택 LLM 응답:", result[:100], "...")
            
            # 최종 선택된 ID 추출
            final_ids = self.parse_final_selection_response(result)
            
            # ID에 해당하는 리포트 목록 생성
            id_to_report = {report["id"]: report for report in candidate_reports}
            final_reports = []
            
            # 최종 선택된 순서대로 리포트 추가
            for report_id in final_ids:
                if report_id in id_to_report:
                    final_reports.append(id_to_report[report_id])
                    if len(final_reports) >= top_k:
                        break
            
            # 부족한 경우 순서대로 추가 (LLM이 충분히 선택하지 않은 경우)
            remaining_ids = [r["id"] for r in candidate_reports if r["id"] not in final_ids]
            for report_id in remaining_ids:
                if len(final_reports) >= top_k:
                    break
                final_reports.append(id_to_report[report_id])
            
            print(f"최종 {len(final_reports)}개 리포트 선정 완료")
            return final_reports
            
        except Exception as e:
            print(f"최종 선택 중 오류 발생: {e}")
            # 오류 발생 시 원래 후보 중 상위 top_k개 반환
            return candidate_reports[:top_k]

    def run_llm_sector_retrieval(self, ticker: str, top_k: int = 5, days_ago: int = 14) -> List[dict]:
        """
        LLM을 사용하여 종목과 관련된 섹터 리포트를 검색하고, 해당 리포트의 상세 정보를 반환합니다.
        2단계 필터링을 적용하여 더 정확한 결과를 제공합니다.
        """
        # 1단계: 넓은 범위의 후보 선정 (top_k의 3배)
        first_stage_k = top_k * 2
        report_ids = self.retrieve_related_sector_reports_with_llm(ticker, top_k=first_stage_k, days_ago=days_ago)
        
        if not report_ids:
            return []
        
        # 1단계 결과의 리포트 상세 정보 조회
        candidate_reports = []
        try:
            ids_str = ','.join(str(id) for id in report_ids)
            query = text(f"""
                SELECT id, title, summary, date, source, keyword 
                FROM sector_reports 
                WHERE id IN ({ids_str})
            """)
            
            with self.mysql_engine.connect() as conn:
                results = conn.execute(query).fetchall()
                
                # 결과 처리
                for row in results:
                    candidate_reports.append({
                        "id": row[0],
                        "title": row[1],
                        "summary": row[2],
                        "date": row[3],
                        "source": row[4],
                        "keyword": row[5]
                    })
        except Exception as e:
            print(f"후보 리포트 정보 조회 중 오류 발생: {e}")
            # 오류 발생 시 1단계 결과만이라도 반환
            return report_ids[:top_k]
        
        # 후보가 top_k 이하면 추가 필터링 없이 반환
        if len(candidate_reports) <= top_k:
            return [report["id"] for report in candidate_reports]
        
        print(f"2단계 필터링: {len(candidate_reports)}개 후보 리포트 중 최적의 {top_k}개 선택 중...")
        
        # 2단계: 상세 정보를 활용한 정밀 필터링
        final_reports = self.refine_report_selection(ticker, candidate_reports, top_k)
        
        return [report["summary"] for report in final_reports] if final_reports else []
        # return [report["id"] for report in final_reports]
        # 테스트할거면 위에 주석 풀고 그 위에거 주석처리
# if __name__ == "__main__":
#     """
#     SectorTool을 활용한 종목 관련 섹터 리포트 검색 예시
    
#     이 스크립트는 다음 작업을 수행합니다:
#     1. .env 파일에서 MySQL, MongoDB, Upstage API 연결 정보를 로드합니다.
#     2. SectorTool 인스턴스를 초기화합니다.
#     3. 예시 티커(SK하이닉스: 005830)에 대한 관련 섹터 리포트를 LLM으로 검색합니다.
#     4. 검색된 리포트 ID 목록을 출력합니다.
#     5. 각 ID에 해당하는 리포트의 제목과 요약 내용을 조회하여 표시합니다.
    
#     커맨드라인에서 실행 방법:
#     $ python tools/sector_tool_llm.py
#     """
#     # .env 파일 로드
#     load_dotenv()
#     mysql_url = os.environ["MYSQL_URL"]
#     mongo_url = os.environ["MONGO_URL"]
#     upstage_api_key = os.environ["UPSTAGE_API_KEY"]

#     sectortool = SectorTool(mysql_url=mysql_url, mongo_url=mongo_url, upstage_api_key=upstage_api_key)  

#     # 검색할 예시 종목 티커 (삼양식품)
#     example_ticker = "069960"
#     days = 14  # 최근 2주 데이터 검색
    
#     # 종목 이름 가져오기
#     stock_name = sectortool.get_stock_name(example_ticker)
#     stock_display = f"{stock_name}({example_ticker})" if stock_name else f"티커 {example_ticker}"
    
#     print(f"\n{stock_display}와(과) 관련된 최근 {days}일 내 섹터 리포트를 LLM으로 검색합니다...")
    
#     # LLM을 통해 관련 섹터 리포트의 ID 목록 검색
#     report_ids = sectortool.run_llm_sector_retrieval(ticker=example_ticker, top_k=5, days_ago=days)
    
#     print(f"\n{stock_display}와(과) 관련된 섹터 리포트 ID:")
#     # print(report_ids)
    
#     # 각 ID에 해당하는 리포트 정보 조회 및 출력
#     if report_ids:
#         print(f"\n{stock_display} 관련 리포트 상세 정보:")
        
#         # MySQL에서 리포트 정보 조회를 위한 쿼리
#         ids_str = ','.join(str(id) for id in report_ids)
#         print('디버깅', ids_str)
#         query = text(f"""
#             SELECT id, title, summary, date, source 
#             FROM sector_reports 
#             WHERE id IN ({ids_str})
#         """)
        
#         try:
#             with sectortool.mysql_engine.connect() as conn:
#                 results = conn.execute(query).fetchall()
                
#                 # 결과가 report_ids의 순서와 일치하지 않을 수 있으므로 ID 기준으로 정렬
#                 id_to_report = {row[0]: row for row in results}
                
#                 for idx, report_id in enumerate(report_ids, 1):
#                     if report_id in id_to_report:
#                         row = id_to_report[report_id]
#                         print(f"\n[{idx}] ID: {row[0]}")
#                         print(f"제목: {row[1]}")
#                         print(f"날짜: {row[3]}")
#                         print(f"출처: {row[4]}")
#                         print(f"요약: {row[2][:200]}..." if len(row[2]) > 200 else f"요약: {row[2]}")
#         except Exception as e:
#             print(f"리포트 정보 조회 중 오류 발생: {e}")
#     else:
#         print(f"{stock_display}와(과) 관련된 섹터 리포트를 찾을 수 없습니다.")