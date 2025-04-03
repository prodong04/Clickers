# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class MacroItem(scrapy.Item):
    title = scrapy.Field(
        serializer=str, 
        metadata={"description": "제목"}
    )
    source = scrapy.Field(
        serializer=str, 
        metadata={"description": "제공출처"}
    )
    date = scrapy.Field(
        serializer=str, 
        metadata={"description": "작성일"}
    )
    file_url = scrapy.Field(
        serializer=str, 
        metadata={"description": "파일링크"}
    )
    summary = scrapy.Field(
        serializer=str, 
        metadata={"description": "요약"}
    )

class SectorItem(scrapy.Item):
    title = scrapy.Field(
        serializer=str, 
        metadata={"description": "제목"}
    )
    source = scrapy.Field(
        serializer=str, 
        metadata={"description": "제공출처"}
    )
    date = scrapy.Field(
        serializer=str, 
        metadata={"description": "작성일"}
    )
    file_url = scrapy.Field(
        serializer=str, 
        metadata={"description": "파일링크"}
    )
    summary = scrapy.Field(
        serializer=str, 
        metadata={"description": "요약"}
    )

class StockItem(scrapy.Item):
    stock_name = scrapy.Field(
        serializer=str, 
        metadata={"description": "종목명"}
    )
    ticker = scrapy.Field(
        serializer=str, 
        metadata={"description": "종목코드"}
    )
    title = scrapy.Field(
        serializer=str, 
        metadata={"description": "제목"}
    )
    source = scrapy.Field(
        serializer=str, 
        metadata={"description": "제공출처"}
    )
    date = scrapy.Field(
        serializer=str, 
        metadata={"description": "작성일"}
    )
    file_url = scrapy.Field(
        serializer=str, 
        metadata={"description": "파일링크"}
    )
    summary = scrapy.Field(
        serializer=str, 
        metadata={"description": "요약"}
    )