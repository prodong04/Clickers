from dotenv import load_dotenv
load_dotenv()

BOT_NAME = "crawler_agent"
SPIDER_MODULES = ["crawler_agent.spiders"]
NEWSPIDER_MODULE = "crawler_agent.spiders"
ROBOTSTXT_OBEY = False
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"