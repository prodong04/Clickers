# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import requests
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse
from itemadapter import ItemAdapter
from crawler_agent.summary_gemma import summarization
load_dotenv()

class ItemPipeline:

    def __init__(self):
        self.conn = mysql.connector.connect(
            host = os.getenv("SQL_HOST"),
            user = os.getenv("SQL_USER"),
            password = os.getenv("SQL_PW"),
            database = os.getenv("SQL_DB"),
            charset = os.getenv("SQL_CHARSET")
        )
        self.cur = self.conn.cursor()

    def process_item(self, item, spider):

        ## case handling for stock, sector, and macro reports.
        adapter = ItemAdapter(item)
        field_names = adapter.field_names()
        item_type = "stock" if "ticker" in field_names else "sector"

        ## Strip all unnecessary spaces from string-type items.
        for field_name in field_names:
            value = adapter.get(field_name)
            try:
                adapter[field_name] = value.strip()
            except AttributeError as e:
                continue
        
        ## download file in temporary disk space.
        file_url = adapter.get("file_url")
        if not file_url:
            raise ValueError("file_url is missing in the item")
        file_name = os.path.basename(urlparse(file_url).path)
        file_path = f"/tmp/{file_name}"

        try:
            response = requests.get(file_url, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # summarize pdf.
            summary = summarization(category=item_type, fname=file_path)

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download {file_url}: {e}")

        finally:
            ## delete the pdf file from temporary disk space.
            if os.path.exists(file_path):
                os.remove(file_path)

        adapter["summary"] = summary
        table_name = f"{item_type}_reports"

        # SQL 실행 및 예외 처리
        try:
            if item_type == "stock":
                sql = f"""
                    INSERT INTO {table_name} (stock_name, ticker, title, source, file_url, date, summary)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    adapter["stock_name"],
                    adapter["ticker"],
                    adapter["title"],
                    adapter["source"],
                    adapter["file_url"],
                    datetime.strptime(adapter["date"], '%Y-%m-%d %H:%M:%S'),
                    adapter["summary"]
                )
            else:
                sql = f"""
                    INSERT INTO {table_name} (title, source, file_url, date, summary)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    adapter["title"],
                    adapter["source"],
                    adapter["file_url"],
                    adapter["date"],
                    adapter["summary"]
                )

            self.cur.execute(sql, values)
            self.conn.commit()
            
        except mysql.connector.Error as e:
            self.conn.rollback()  # 오류 발생 시 롤백
            raise RuntimeError(f"Database insertion error: {e}")

        return item
    
    def close_spider(self, spider):
        ## Close cursor & connection to database 
        self.cur.close()
        self.conn.close()