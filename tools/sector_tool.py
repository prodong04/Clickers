import os
import re
import json
import pickle
import hashlib
from pathlib import Path
import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
from dotenv import load_dotenv

from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class SectorTool:
    """
    MySQL에서 종목 정보를 가져와 MongoDB Vector Search를 통해 관련 섹터 리포트를 검색하는 도구.
    
    주요 기능:
    1. MySQL → MongoDB 데이터 동기화
    2. 임베딩 벡터 생성 및 캐싱
    3. 벡터 검색을 통한 관련 섹터 리포트 조회
    4. 유사도 임계값 기반 필터링
    """
    def __init__(self, mysql_url: str = None, mongo_url: str = None, upstage_api_key: str = None,
                 cache_dir: str = "./data/cache"):
        """
        SectorTool 초기화
        
        Args:
            mysql_url: MySQL 연결 URL
            mongo_url: MongoDB 연결 URL
            upstage_api_key: Upstage API 키
            cache_dir: 임베딩 캐시 저장 디렉토리
        """
        # 캐시 디렉토리 설정 및 생성
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_cache = self.load_embedding_cache()
        
        # Upstage 클라이언트 초기화
        self.client = OpenAI(
            api_key=upstage_api_key,
            base_url="https://api.upstage.ai/v1"
        )

        # MySQL 연결 설정
        self.mysql_engine = create_engine(mysql_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.mysql_engine)

        # MongoDB Atlas 연결
        self.mongo_client = MongoClient(mongo_url, server_api=ServerApi('1'))
        self.database = self.mongo_client[os.environ.get("MONGO_DB", "alpha-agent")]
        self.collection = self.database[os.environ.get("MONGO_COLLECTION", "sector-embedding")]
        
        # 임베딩 생성 설정
        self.embedding_model = "solar-embedding-1-large-passage"
        self.embedding_dimension = 1024

    # ----------- 임베딩 관련 메서드 ----------- #
    
    def get_embedding(self, text: str) -> List[float]:
        """
        텍스트에 대한 임베딩 벡터 생성 (캐시 활용)
        """
        if not text:
            return [0] * self.embedding_dimension
            
        # 캐시 키 생성 (텍스트 해시)
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        # 캐시에서 임베딩 확인
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        # 임베딩 생성
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            
            # 캐시에 저장
            self.embedding_cache[cache_key] = embedding
            
            # 주기적으로 캐시 저장 (캐시 크기가 1000개 이상일 때)
            if len(self.embedding_cache) % 1000 == 0:
                self.save_embedding_cache()
                
            return embedding
            
        except Exception as e:
            print(f"임베딩 생성 오류: {e}")
            return [0] * self.embedding_dimension
    
    def get_batch_embeddings(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        여러 텍스트의 임베딩을 배치로 생성 (캐시 활용)
        """
        if not texts:
            return []
            
        results = []
        cache_miss_texts = []
        cache_miss_indices = []
        
        # 캐시 확인
        for i, text in enumerate(texts):
            if not text:
                results.append([0] * self.embedding_dimension)
                continue
                
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self.embedding_cache:
                results.append(self.embedding_cache[cache_key])
            else:
                results.append(None)  # 임시 None 값
                cache_miss_texts.append(text)
                cache_miss_indices.append(i)
        
        # 캐시에 없는 텍스트만 배치로 처리
        if cache_miss_texts:
            print(f"캐시 미스: {len(cache_miss_texts)}개 임베딩 생성 필요")
            
            # 배치 단위로 처리
            for i in range(0, len(cache_miss_texts), batch_size):
                batch = cache_miss_texts[i:i+batch_size]
                batch_indices = cache_miss_indices[i:i+batch_size]
                
                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.embedding_model
                    )
                    
                    # 결과 저장 및 캐싱
                    for j, (text, index) in enumerate(zip(batch, batch_indices)):
                        embedding = response.data[j].embedding
                        cache_key = hashlib.md5(text.encode()).hexdigest()
                        self.embedding_cache[cache_key] = embedding
                        results[index] = embedding
                        
                    print(f"배치 {i//batch_size + 1}/{(len(cache_miss_texts)-1)//batch_size + 1} 완료")
                    
                except Exception as e:
                    print(f"배치 임베딩 생성 오류: {e}")
                    # 오류 시 개별 처리로 폴백
                    for text, index in zip(batch, batch_indices):
                        try:
                            single_response = self.client.embeddings.create(
                                input=text,
                                model=self.embedding_model
                            )
                            embedding = single_response.data[0].embedding
                            cache_key = hashlib.md5(text.encode()).hexdigest()
                            self.embedding_cache[cache_key] = embedding
                            results[index] = embedding
                        except:
                            results[index] = [0] * self.embedding_dimension
        
        # 캐시 저장
        self.save_embedding_cache()
        
        return results
    
    def load_embedding_cache(self) -> Dict[str, List[float]]:
        """임베딩 캐시 로드"""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    cache = pickle.load(f)
                print(f"임베딩 캐시 로드 완료: {len(cache)}개 항목")
                return cache
            except Exception as e:
                print(f"캐시 로드 오류: {e}")
        return {}
    
    def save_embedding_cache(self):
        """임베딩 캐시 저장"""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(self.embedding_cache, f)
            print(f"임베딩 캐시 저장 완료: {len(self.embedding_cache)}개 항목")
        except Exception as e:
            print(f"캐시 저장 오류: {e}")
    
    # ----------- 데이터 조회 메서드 ----------- #
    
    def get_stock_summary(self, ticker: str) -> str:
        """
        종목 티커로 해당 종목의 키워드와 설명 정보를 가져옴
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
            # 키워드 추출
            keyword_pattern = r"종목 키워드:\s*(.*?)(?:\\|\n)"
            m_keyword = re.search(keyword_pattern, summary)
            keyword_text = m_keyword.group(1).strip() if m_keyword else ""

            # 설명 추출
            description_pattern = r"(?:\d+\.\s*)?종목 설명:\s*(.*?)(?:\\|\n)"
            m_desc = re.search(description_pattern, summary)
            description_text = m_desc.group(1).strip() if m_desc else ""

            return f"{keyword_text}\n\n{description_text}"
        else:
            return ""
    
    def get_stock_name(self, ticker: str) -> str:
        """종목 티커로 종목명 조회"""
        query = text("""
            SELECT stock_name
            FROM stock_reports
            WHERE ticker = :ticker
            LIMIT 1
        """)
        with self.mysql_engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker}).fetchone()
        
        return result[0] if result else ""
    
    # ----------- 데이터 동기화 메서드 ----------- #
    
    def import_sector_reports_to_mongodb(self, days_lookback: int = None, batch_size: int = 20) -> Tuple[int, int]:
        """
        MySQL의 섹터 리포트를 MongoDB로 임포트하고 임베딩 생성
        
        Args:
            days_lookback: 최근 n일 데이터만 처리 (None이면 모든 데이터)
            batch_size: 배치 처리 크기
            
        Returns:
            (삽입된 문서 수, 업데이트된 임베딩 수)
        """
        # 날짜 필터링 조건 추가
        date_condition = ""
        if days_lookback:
            from_date = datetime.datetime.now() - datetime.timedelta(days=days_lookback)
            from_date_str = from_date.strftime("%Y-%m-%d")
            date_condition = f"WHERE date >= '{from_date_str}'"
            print(f"최근 {days_lookback}일 동안의 데이터만 처리합니다 (>= {from_date_str})")
        
        # 1. MySQL에서 데이터 가져오기
        query = text(f"""
            SELECT id, date, title, summary, file_url, source, keyword 
            FROM sector_reports
            {date_condition}
            ORDER BY date DESC
        """)
        
        with self.mysql_engine.connect() as conn:
            results = conn.execute(query).fetchall()
        
        print(f"MySQL에서 {len(results)}개의 섹터 리포트를 가져왔습니다.")
        if not results:
            return (0, 0)
        
        # 처리 카운터
        inserted_count = 0
        skipped_count = 0
        
        # 2. MySQL 데이터를 MongoDB에 삽입 (중복 건너뛰기)
        for i, row in enumerate(results):
            mysql_id = row[0]
            
            # 이미 같은 MySQL ID의 문서가 MongoDB에 있는지 확인
            existing_doc = self.collection.find_one({"mysql_id": mysql_id})
            
            if existing_doc:
                skipped_count += 1
                continue
            
            try:
                # 레코드 데이터 추출
                date_value = row[1]
                title = row[2]
                summary = row[3]
                file_url = row[4]
                source = row[5]
                keyword = row[6]
                
                # date 값 변환
                if isinstance(date_value, datetime.date) and not isinstance(date_value, datetime.datetime):
                    date_value = datetime.datetime.combine(date_value, datetime.time.min)
                
                # 요약 필드가 없으면 건너뛰기
                if not summary:
                    continue
                
                # MongoDB에 저장할 문서 생성
                document = {
                    "mysql_id": mysql_id,
                    "date": date_value,
                    "title": title,
                    "summary": summary,
                    "file_url": file_url,
                    "source": source,
                    "keyword": keyword
                }
                
                # MongoDB에 문서 추가
                result = self.collection.insert_one(document)
                
                if result.inserted_id:
                    inserted_count += 1
                
                # 진행 상황 출력
                if (i+1) % 50 == 0 or i+1 == len(results):
                    print(f"[{i+1}/{len(results)}] MongoDB 저장 중 - 삽입: {inserted_count}, 건너뜀: {skipped_count}")
                    
            except Exception as e:
                print(f"[{i+1}/{len(results)}] ID {mysql_id} 저장 중 오류 발생: {e}")
        
        # 3. 배치 처리로 임베딩 생성 및 저장
        print("\n임베딩이 필요한 문서를 확인합니다...")
        
        # 임베딩이 없는 문서만 조회
        no_embedding_docs = list(self.collection.find(
            {"$or": [
                {"summary_embedding": {"$exists": False}},
                {"summary_embedding": None}
            ]}
        ))
        
        print(f"임베딩이 필요한 문서: {len(no_embedding_docs)}개")
        if not no_embedding_docs:
            return (inserted_count, 0)
        
        # 배치 처리를 위한 준비
        updated_count = 0
        
        # 키워드 텍스트 목록 및 ID 매핑
        batch_texts = []
        doc_ids = []
        
        for doc in no_embedding_docs:
            keyword = doc.get("keyword", "")
            if keyword:
                batch_texts.append(keyword)
                doc_ids.append(doc["_id"])
        
        if not batch_texts:
            return (inserted_count, 0)
        
        # 배치 단위로 임베딩 생성
        print(f"총 {len(batch_texts)}개 문서의 임베딩을 생성합니다...")
        
        for i in range(0, len(batch_texts), batch_size):
            current_batch = batch_texts[i:i+batch_size]
            current_ids = doc_ids[i:i+batch_size]
            
            try:
                # 배치 임베딩 생성
                batch_embeddings = self.get_batch_embeddings(current_batch)
                
                # 개별 문서 업데이트
                for j, (doc_id, embedding) in enumerate(zip(current_ids, batch_embeddings)):
                    self.collection.update_one(
                        {"_id": doc_id},
                        {"$set": {"summary_embedding": embedding}}
                    )
                    updated_count += 1
                
                # 진행 상황 출력
                current_batch_num = i // batch_size + 1
                total_batches = (len(batch_texts) - 1) // batch_size + 1
                print(f"배치 {current_batch_num}/{total_batches}: {len(current_batch)}개 임베딩 완료 (총 {updated_count}/{len(batch_texts)})")
                
            except Exception as e:
                print(f"배치 {i//batch_size+1} 임베딩 생성 중 오류: {e}")
        
        # 캐시 최종 저장
        self.save_embedding_cache()
        
        return (inserted_count, updated_count)
    
    # ----------- 검색 메서드 ----------- #
    
    def retrieve_top_k_sector_summaries(self, ticker: str, top_k: int = 5, days_ago: int = 14, 
                                       score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        종목 관련 섹터 리포트 검색
        
        Args:
            ticker: 종목 티커
            top_k: 반환할 최대 문서 수
            days_ago: 최근 n일 데이터만 검색
            score_threshold: 유사도 최소 임계값
        
        Returns:
            관련 섹터 리포트 정보 목록 (유사도 점수 포함)
        """
        # 종목 정보 가져오기
        stock_summary = self.get_stock_summary(ticker)
        if not stock_summary:
            return [{"summary": "MySQL에 해당 종목 summary가 없습니다.", "score": 0.0}]

        # 검색을 위한 임베딩 생성
        query_embed = self.get_embedding(stock_summary)
        
        # 시간 필터링
        from_date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        
        # MongoDB 검색을 다양한 방식으로 시도
        results = []
        try:
            # 1. Vector Search 시도
            try:
                # ANN 벡터 검색
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "sec-index",
                            "path": "summary_embedding",
                            "queryVector": query_embed,
                            "numCandidates": max(top_k * 3, 50),
                            "limit": top_k * 3
                        }
                    },
                    {
                        "$match": {
                            "date": {"$gte": from_date}
                        }
                    }
                ]
                results = list(self.collection.aggregate(pipeline))
            except Exception as e:
                print(f"Vector Search 오류: {e}")
                
                # 2. 대체 방식 시도 ($search 사용)
                try:
                    pipeline = [
                        {
                            "$search": {
                                "index": "sec-index",
                                "knnBeta": {
                                    "vector": query_embed,
                                    "path": "summary_embedding",
                                    "k": top_k * 3
                                }
                            }
                        },
                        {
                            "$match": {
                                "date": {"$gte": from_date}
                            }
                        }
                    ]
                    results = list(self.collection.aggregate(pipeline))
                except Exception as e2:
                    print(f"$search 시도 오류: {e2}")
                    
            # 3. 최후 수단: 모든 임베딩 문서 로드 후 메모리에서 코사인 유사도 계산
            if not results:
                print("대체 검색 방법 사용: 메모리 기반 코사인 유사도 계산")
                results = list(self.collection.find({"date": {"$gte": from_date}}))
                
            print(f"총 {len(results)}개 문서 검색됨")
            
            # 임베딩 기반 코사인 유사도 계산 및 필터링
            filtered_results = []
            
            print(f"코사인 유사도 계산 및 임계값({score_threshold}) 필터링 시작...")
            for i, doc in enumerate(results):
                doc_embed = doc.get("summary_embedding")
                if not doc_embed:
                    continue
                    
                # 코사인 유사도 계산
                try:
                    cos_sim = cosine_similarity([query_embed], [doc_embed])[0][0]
                    
                    if cos_sim >= score_threshold:
                        doc_info = {
                            "id": doc.get("mysql_id"),
                            "title": doc.get("title", ""),
                            "summary": doc.get("summary", ""),
                            "date": doc.get("date", ""),
                            "source": doc.get("source", ""),
                            "keyword": doc.get("keyword", ""),
                            "score": float(cos_sim)
                        }
                        filtered_results.append(doc_info)
                        print(f"문서 {i+1}/{len(results)}: 유사도 {cos_sim:.4f} ✓")
                    else:
                        print(f"문서 {i+1}/{len(results)}: 유사도 {cos_sim:.4f} ✗")
                except Exception as e:
                    print(f"유사도 계산 오류 (문서 {i+1}): {e}")
            
            # 결과 정렬 및 제한
            filtered_results.sort(key=lambda x: x["score"], reverse=True)
            result_count = len(filtered_results)
            filtered_results = filtered_results[:top_k]
            
            print(f"유사도 필터링 결과: {result_count}개 중 {len(filtered_results)}개 선택됨")
            
            if not filtered_results:
                return [{"summary": f"임계값({score_threshold}) 이상의 유사한 섹터 리포트가 없습니다.", "score": 0.0}]
                
            return filtered_results
            
        except Exception as e:
            print(f"섹터 리포트 검색 중 오류 발생: {e}")
            return [{"summary": f"검색 중 오류 발생: {str(e)}", "score": 0.0}]
    
    # ----------- 실행 메서드 ----------- #
    
    def run(self, ticker: str, top_k: int = 5, days_ago: int = 14, score_threshold: float = 0.5, days_lookback: int = 0) -> List[str]:
        """
        종목 관련 섹터 리포트 검색 실행 (간편 인터페이스)
        
        Returns:
            검색된 섹터 summary 문자열들의 리스트
        """
        
        self.import_sector_reports_to_mongodb(days_lookback=days_lookback)

        results = self.retrieve_top_k_sector_summaries(
            ticker, 
            top_k=top_k, 
            days_ago=days_ago, 
            score_threshold=score_threshold
        )
        
        if isinstance(results[0], dict):
            return [doc["summary"] for doc in results]
        else:
            return results

# 스크립트로 실행될 때의 코드
if __name__ == "__main__":
    # 환경 변수 로드
    load_dotenv()
    mysql_url = os.environ["MYSQL_URL"]
    mongo_url = os.environ["MONGO_URL"]
    upstage_api_key = os.environ["UPSTAGE_API_KEY"]

    # 인스턴스 생성
    sectortool = SectorTool(
        mysql_url=mysql_url, 
        mongo_url=mongo_url, 
        upstage_api_key=upstage_api_key
    )

    example_ticker = "005930"  # 삼성전자
    stock_name = sectortool.get_stock_name(example_ticker)
    stock_display = f"{stock_name}({example_ticker})" if stock_name else f"티커 {example_ticker}"
    
    print(f"\n{stock_display}와(과) 관련된 섹터 리포트를 검색합니다...")
    summaries = sectortool.run(example_ticker, top_k=5, days_ago=14, days_lookback=14, score_threshold=0.4)
    
    print(f"\n{stock_display} 관련 섹터 리포트 ({len(summaries)}개):")
    for idx, summary in enumerate(summaries, start=1):
        print(f"\n[{idx}]\n{summary[:400]}...")