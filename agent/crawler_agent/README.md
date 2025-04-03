
# Crawler Agent
<div align=left> 
  <img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white"> 
  <img src="https://img.shields.io/badge/pytorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white">
  <img src="https://img.shields.io/badge/scrapy-60A839?style=for-the-badge&logo=scrapy&logoColor=white"> 
  <img src="https://img.shields.io/badge/langchain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white"> 
  <br>
</div>

## Overview
This is a crawler agent for the following purposes:
- Scrape analyst reports and their metadata from Naver Pay Securities.
- Summarize the contents of PDFs using a LLM model.
- Send the acquired data to a cloud storage.

## Current Status
- [X]  Naver Pay Securities web-scraper on local device
- [X]  Automatic date adjustment for each run
- [X]  Summarization module using LLM
- [ ]  Data transmission to cloud storage
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

## File Structure
```bash
    agent/crawler_agent
    |-- README.md
    |-- crawler_agent
    |   |-- __init__.py
    |   |-- middlewares.py
    |   |-- pipelines.py         ## determines how items are processed
    |   |-- settings.py          ## scrapy settings
    |   |-- spiders
    |   |   |-- __init__.py
    |   |   |-- last_run.json    ## save and load last execution time
    |   |   |-- macro.py         ## spider for macro analyst reports
    |   |   |-- sector.py        ## spider for sector analyst reports
    |   |   `-- stock.py         ## spider for stock analyst reports
    |   `-- summary.py           ## summarizer module
    |-- environment.yaml
    `-- scrapy.cfg
```

## Installation

```bash
  cd Agent/agent/crawler_agent
  conda create --name crawl --file environment.yaml
  conda activate crawl
```

## Deployment

```bash
  cd Agent/agent/crawler_agent
  scrapy crawl macro
  scrapy crawl sector
  scrapy crawl stock
```

## Contributors

- [@Hoesu](https://github.com/Hoesu)
- [@imsuviiix](https://github.com/imsuviiix)