import re
import os
import requests
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse
from itemadapter import ItemAdapter
from crawler_agent.items import MacroItem
from crawler_agent.items import SectorItem
from crawler_agent.items import StockItem
from crawler_agent.summarizer import summarization
load_dotenv()

class ItemPipeline:

    def __init__(self):
        self.conn = mysql.connector.connect(
            host=os.getenv('SQL_HOST'),
            port=os.getenv('SQL_PORT'),
            user=os.getenv('SQL_USER'),
            password=os.getenv('SQL_PW'),
            db=os.getenv('SQL_DB'),
            charset='utf8mb4'
        )
        self.cur = self.conn.cursor()

    @staticmethod
    def parse_document(filename):
        api_key = os.getenv("UPSTAGE_API_KEY")
        url = "https://api.upstage.ai/v1/document-digitization"
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"document": open(filename, "rb")}
        data = {"ocr": "force", "base64_encoding": "['table']", "model": "document-parse"}
        response = requests.post(url, headers=headers, files=files, data=data)
        return response.json()
    
    @staticmethod
    def parser_html(html_text):
        pattern = r"'>(.*?)</p>"
        result = re.search(pattern, html_text, re.DOTALL)
        if result:
            text = result.group(1)
            text = re.sub(r'<br>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
        return text

    def process_item(self, item, spider):
        ## case handling for stock, sector, and macro reports.
        adapter = ItemAdapter(item)
        field_names = adapter.field_names()
        if isinstance(item, MacroItem):
            item_type = "macro"
        elif isinstance(item, SectorItem):
            item_type = "sector"
        elif isinstance(item, StockItem):
            item_type = "stock"
        else:
            raise ValueError("Invalid item type")

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
            response = self.parse_document(file_path)
            summary = [self.parser_html(element['content']['html']) for element in response['elements'] if element.get('category') == 'paragraph']
            summary = "".join(summary)
            keyword = summarization(summary, category=item_type)

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download {file_url}: {e}")

        finally:
            ## delete the pdf file from temporary disk space.
            if os.path.exists(file_path):
                os.remove(file_path)

        adapter["summary"] = summary
        adapter["keyword"] = keyword
        table_name = f"{item_type}_reports"

        # SQL 실행 및 예외 처리
        try:
            if item_type == "stock":
                sql = f"""
                    INSERT INTO {table_name} (stock_name, ticker, title, source, file_url, date, summary, keyword)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    adapter["stock_name"],
                    adapter["ticker"],
                    adapter["title"],
                    adapter["source"],
                    adapter["file_url"],
                    datetime.strptime(adapter["date"], '%y.%m.%d').strftime('%Y-%m-%d %H:%M:%S'),
                    adapter["summary"],
                    adapter["keyword"]
                )
            else:
                sql = f"""
                    INSERT INTO {table_name} (stock_name, ticker, title, source, file_url, date, summary, keyword)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (
                    None,
                    None,
                    adapter["title"],
                    adapter["source"],
                    adapter["file_url"],
                    datetime.strptime(adapter["date"], '%y.%m.%d').strftime('%Y-%m-%d %H:%M:%S'),
                    adapter["summary"],
                    adapter["keyword"]
                )
            self.cur.execute(sql, values)
            self.conn.commit()
            
        except mysql.connector.Error as e:
            self.conn.rollback()
            raise RuntimeError(f"Database insertion error: {e}")

        return item
    
    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()