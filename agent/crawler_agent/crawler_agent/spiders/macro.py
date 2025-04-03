import json
import scrapy
from pathlib import Path
from urllib.parse import urljoin
from datetime import date, timedelta
from crawler_agent.items import MacroItem

class NaverSecuritiesMacroSpider(scrapy.Spider):

    name = "macro"
    custom_settings = {
    "FEEDS" : {
        f"results/MACRO_{date.today().isoformat()}.jsonl": {"format": "jsonlines", "overwrite": True}
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
        self.start_urls = [
            f"https://finance.naver.com/research/economy_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}",
            f"https://finance.naver.com/research/debenture_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}"
        ]

    def set_time(self):
        json_path = Path(__file__).resolve().parent / "last_run.json"
        try:
            with json_path.open("r+") as f:
                data = json.load(f)
                sdate = date.fromisoformat(data["macro"]["last_run"]) + timedelta(days=1)
                edate = date.today()
                data["macro"]["last_run"] = edate.isoformat()
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                return sdate.isoformat(), edate.isoformat()
        except FileNotFoundError as e:
            return None

    def parse(self, response):
        reports = response.xpath("//tr[td[contains(@style, 'padding-left:10')]]")
        for report in reports:
            macro_item = MacroItem()
            macro_item['title'] = report.xpath('./td[1]/a/text()').get()                  ## 제목
            macro_item['source'] = report.xpath('./td[2]/text()').get()                   ## 제공출처
            macro_item['file_url'] = report.xpath('./td[3]/a/@href').get()                ## 파일링크
            macro_item['date'] = report.xpath('./td[4]/text()').get()                     ## 작성일
            macro_item['summary'] = self.parse_pdf(macro_item['file_url'])                ## 요약
            yield macro_item

        next_page = response.xpath("//td[@class='on']/following-sibling::td[1]")
        if next_page.xpath('a/@href').get():
            next_page_url = urljoin('https://finance.naver.com/',next_page.xpath('a/@href').get())
            yield response.follow(next_page_url, callback = self.parse)
        else:
            return

    def parse_pdf(self, file_url: str) -> None:
        return None 