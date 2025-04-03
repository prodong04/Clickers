import json
import scrapy
from pathlib import Path
from urllib.parse import urljoin
from datetime import date, timedelta
from crawler_agent.items import StockItem

class NaverSecuritiesStockSpider(scrapy.Spider):

    name = "stock"
    custom_settings = {
    "FEEDS" : {
        f"results/STOCK_{date.today().isoformat()}.jsonl": {"format": "jsonlines", "overwrite": True}
    },
    "ITEM_PIPELINES" : {
        "crawler_agent.pipelines.ItemPipeline": 300
    },
    #"SPIDER_MIDDLEWARES" : {
    #    "crawler_agent.middlewares.ScrapeOpsFakeBrowserHeaderAgentMiddleware": 543
    #}
    }

    def __init__(self):
        super().__init__()
        self.sdate, self.edate = self.set_time()
        self.allowed_domains = ["finance.naver.com"]
        self.start_urls = [f"https://finance.naver.com/research/company_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}"]
    
    def set_time(cls):
        json_path = Path(__file__).resolve().parent / "last_run.json"
        try:
            with json_path.open("r+") as f:
                data = json.load(f)
                sdate = date.fromisoformat(data["stock"]["last_run"]) + timedelta(days=1)
                edate = date.today()
                data["stock"]["last_run"] = edate.isoformat()
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                return sdate.isoformat(), edate.isoformat()
        except FileNotFoundError as e:
            return None

    def parse(self, response):
        reports = response.xpath("//tr[td[contains(@style, 'padding-left:10')]]")
        for report in reports:
            stock_item = StockItem()
            stock_item['stock_name'] = report.xpath('./td[1]/a/text()').get()             ## 종목명
            stock_item['ticker'] =  report.xpath('./td[1]/a/@href').get().split('=')[-1]  ## 종목코드
            stock_item['title'] = report.xpath('./td[2]/a/text()').get()                  ## 제목
            stock_item['source'] = report.xpath('./td[3]/text()').get()                   ## 제공출처
            stock_item['file_url'] = report.xpath('./td[4]/a/@href').get()                ## 파일링크
            stock_item['date'] = report.xpath('./td[5]/text()').get()                     ## 작성일
            stock_item['summary'] = self.parse_pdf(stock_item['file_url'])                ## 요약
            yield stock_item

        next_page = response.xpath("//td[@class='on']/following-sibling::td[1]")
        if next_page.xpath('a/@href').get():
            next_page_url = urljoin('https://finance.naver.com/',next_page.xpath('a/@href').get())
            yield response.follow(next_page_url, callback = self.parse)
        else:
            return

    def parse_pdf(self, file_url: str) -> None:
        return None