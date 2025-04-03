import json
import scrapy
from pathlib import Path
from urllib.parse import urljoin
from datetime import date, timedelta
from crawler_agent.items import SectorItem

class NaverSecuritiesSectorSpider(scrapy.Spider):

    name = "sector"
    custom_settings = {
    "FEEDS" : {
        f"results/SECTOR_{date.today().isoformat()}.jsonl": {"format": "jsonlines", "overwrite": True}
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
            f"https://finance.naver.com/research/market_info_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}",
            f"https://finance.naver.com/research/invest_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}",
            f"https://finance.naver.com/research/industry_list.naver?keyword=&brokerCode=&searchType=writeDate&writeFromDate={self.sdate}&writeToDate={self.edate}"
            ]

    def set_time(self):
        json_path = Path(__file__).resolve().parent / "last_run.json"
        try:
            with json_path.open("r+") as f:
                data = json.load(f)
                sdate = date.fromisoformat(data["sector"]["last_run"]) + timedelta(days=1)
                edate = date.today()
                data["sector"]["last_run"] = edate.isoformat()
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                return sdate.isoformat(), edate.isoformat()
        except FileNotFoundError as e:
            return None

    def parse(self, response):

        checker = response.xpath("//table[@class='type_1']//th[1]/text()").get()
        if checker == '분류':
            reports = response.xpath("//tr[td[contains(@style, 'padding-left:10')]]")
            for report in reports:
                sector_item = SectorItem()
                sector_item['title'] = report.xpath('./td[2]/a/text()').get()                   ## 제목
                sector_item['source'] = report.xpath('./td[3]/text()').get()                    ## 제공출처
                sector_item['file_url'] = report.xpath('./td[4]/a/@href').get()                 ## 파일링크
                sector_item['date'] = report.xpath('./td[5]/text()').get()                      ## 작성일
                sector_item['summary'] = self.parse_pdf(sector_item['file_url'])                ## 요약
                yield sector_item
        else:
            reports = response.xpath("//tr[td[contains(@style, 'padding-left:10')]]")
            for report in reports:
                sector_item = SectorItem()
                sector_item['title'] = report.xpath('./td[1]/a/text()').get()                   ## 제목
                sector_item['source'] = report.xpath('./td[2]/text()').get()                    ## 제공출처
                sector_item['file_url'] = report.xpath('./td[3]/a/@href').get()                 ## 파일링크
                sector_item['date'] = report.xpath('./td[4]/text()').get()                      ## 작성일
                sector_item['summary'] = self.parse_pdf(sector_item['file_url'])                ## 요약
                yield sector_item

        next_page = response.xpath("//td[@class='on']/following-sibling::td[1]")
        if next_page.xpath('a/@href').get():
            next_page_url = urljoin('https://finance.naver.com/',next_page.xpath('a/@href').get())
            yield response.follow(next_page_url, callback = self.parse)
        else:
            return

    def parse_pdf(self, file_url: str) -> None:
        return None