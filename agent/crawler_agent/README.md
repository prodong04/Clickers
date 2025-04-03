# Crawler Agent
<div align=left> 
  <img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white"> 
  <img src="https://img.shields.io/badge/scrapy-60A839?style=for-the-badge&logo=scrapy&logoColor=white"> 
  <img src="https://img.shields.io/badge/langchain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white">
  <img src="https://img.shields.io/badge/mysql-4479A1?style=for-the-badge&logo=mysql&logoColor=white">
  <img src="https://img.shields.io/badge/Upstage-1c2437?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyBoZWlnaHQ9IjFlbSIgc3R5bGU9ImZsZXg6bm9uZTtsaW5lLWhlaWdodDoxIiB2aWV3Qm94PSIwIDAgMjQgMjQiIHdpZHRoPSIxZW0iIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHRpdGxlPlVwc2F0ZTwvdGl0bGU+PHBhdGggZD0iTTE5Ljc2MyAwbC0uMzczIDEuMjk3aDIuNTk0TDIyLjM1NCAwaC0yLjU5MXpNMTYuMTkyIDIuMjdsLS4zNzYgMS4yOThoNS41MmwuMzctMS4yOThoLTUuNTE0ek0xMi44OTcgNC41NGwtLjM3NiAxLjI5OGg4LjE2NmwuMzctMS4yOThoLTguMTZ6TTIuODUgNi44MWwtLjM3NyAxLjI5OGgxNy41NjVsLjM3LTEuMjk3SDIuODQ4ek0zLjg4NCA5LjA4MWwtLjM3NiAxLjI5N0gxOS4zOWwuMzctMS4yOTdIMy44ODJ6TTQuMDg4IDI0bC4zNzYtMS4yOTdIMS44NjZMMS41IDI0aDIuNTg4ek03LjY2MiAyMS43M2wuMzc2LTEuMjk3SDIuNTE1TDIuMTUgMjEuNzNoNS41MTN6TTEwLjk1NyAxOS40NTlsLjM3Ni0xLjI5N2gtOC4xN2wtLjM2NiAxLjI5N2g4LjE2ek0yMS4wMDUgMTcuMTg5bC4zNzYtMS4yOTdIMy44MTJsLS4zNjYgMS4yOTdoMTcuNTU5ek0xOS45NjcgMTQuOTE5bC4zNzYtMS4yOTdINC40NjFsLS4zNjYgMS4yOTdoMTUuODcyek0xOC43ODYgMTIuNjQ5bC4zNzYtMS4yOTdINC4yNmwtLjM2NiAxLjI5N2gxNC44OTN6IiBmaWxsPSJ1cmwoI2xvYmUtaWNvbnMtdXBzYXRlLWZpbGwpIj48L3BhdGg+PGRlZnM+PGxpbmVhckdyYWRpZW50IGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIiBpZD0ibG9iZS1pY29ucy11cHNhdGUtZmlsbCIgeDE9IjExLjkyNyIgeDI9IjExLjkyNyIgeTI9IjI0Ij48c3RvcCBvZmZzZXQ9IjAiIHN0b3AtY29sb3I9IiNBRUJDRkUiPjwvc3RvcD48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM4MDVERkEiPjwvc3RvcD48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48L3N2Zz4=">
  <br>
</div>

## Overview
This is a crawler agent for the following purposes:
- Scrape analyst reports and their metadata from Naver Pay Securities.
- Parse PDF documents with upstage document parser API.
- Summarize the refined text data using a LLM model.
- Upload the scraped data to a MySQL database.

## Current Status
- [X]  Naver Pay Securities web-scraper using scrapy
- [X]  Automatic date adjustment for each run
- [X]  Upstage document parser integration into scraping process
- [X]  Summarization module using LLM
- [X]  Data transmission to MySQL database
- [ ]  Automated code execution on designated time

## Data Structure
Analyst reports are categorized into three groups: Stock, Sector, and Macro.

We extract the following list of features for each category.
| Stock reports  | Sector Reports | Macro Reports  |
| -------------- | -------------- | -------------- |
| Stock Name     | -              | -              |
| Ticker         | -              | -              |
| Report Title   | Report Title   | Report Title   |
| Report Source  | Report Source  | Report Source  |
| Date           | Date           | Date           |
| File URL       | File URL       | File URL       |
| Summary        | Summary        | Summary        |
| Keyword        | Keyword        | Keyword        |

## File Structure
```bash
crawler_agent
├── crawler_agent
│   │
│   ├── __init__.py
│   ├── items.py             ## defines items to scrape
│   ├── middlewares.py       ## middleswares for random header generation
│   ├── pipelines.py         ## determines how items are processed
│   ├── settings.py          ## scrapy settings
│   ├── summarizer.py        ## LLM summarizer for keyword extraction
│   │
│   └── spiders
│       ├── __init__.py
│       ├── last_run.json    ## save and load last execution time
│       ├── macro.py         ## spider for macro analyst reports
│       ├── sector.py        ## spider for sector analyst reports
│       └── stock.py         ## spider for stock analyst reports
│
├── environment.yaml
├── README.md
└── scrapy.cfg
```

## Installation

```bash
  cd crawler_agent
  conda create --name crawl --file environment.yaml
  conda activate crawl
```
In addition to setting up conda environment, you must create a .env file with the following environment variables:
```bash
UPSTAGE_API_KEY
SQL_HOST
SQL_PORT
SQL_USER
SQL_PW
SQL_DB
```

## Deployment

Before crawling, make sure to check **last_run.json** and set the start date.
```bash
  cd crawler_agent
  scrapy crawl macro
  scrapy crawl sector
  scrapy crawl stock
```

## Contributors

- [@Hoesu](https://github.com/Hoesu)
- [@imsuviiix](https://github.com/imsuviiix)