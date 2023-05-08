from functools import lru_cache
from pydantic import BaseModel, BaseSettings, Field


class Task(BaseModel):
    name: str
    task_ran: bool = False


def create_schedules() -> dict[str, dict[str, str | bool]]:
    """
        creates schedules to run news scrapping tasks and return them
        TODO - create a route to set the schedules
    :return:
    """
    tasks_schedules = {
        '00:00': Task(name='scrape_news_yahoo', task_ran=False),
        '04:00': Task(name='scrape_news_yahoo', task_ran=False),
        '08:00': Task(name='scrape_news_yahoo', task_ran=False),
        '12:00': Task(name='scrape_news_yahoo', task_ran=False),
        '16:00': Task(name='scrape_news_yahoo', task_ran=False),
        '20:00': Task(name='scrape_news_yahoo', task_ran=False),
        '23:00': Task(name='scrape_news_yahoo', task_ran=False),

        # '01:30': Task(name='alternate_news_sources', task_ran=False),
        # '04:30': Task(name='alternate_news_sources', task_ran=False),
        # '07:30': Task(name='alternate_news_sources', task_ran=False),
        # '10:30': Task(name='alternate_news_sources', task_ran=False),
        # '13:30': Task(name='alternate_news_sources', task_ran=False),
        # '16:30': Task(name='alternate_news_sources', task_ran=False),
        # '19:30': Task(name='alternate_news_sources', task_ran=False),
        # '22:30': Task(name='alternate_news_sources', task_ran=False)
    }
    return tasks_schedules


class DatabaseSettings(BaseSettings):
    SQL_DB_URL: str = Field(..., env='SQL_DB_URL')
    TOTAL_CONNECTIONS: int = Field(default=1000)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class SchedulerSettings(BaseModel):
    """
        keys are scheduled times, values are dicts
        which include the task name and a bool to indicate the task already ran

    """
    schedule_times: dict[str, Task] = Field(default_factory=lambda: create_schedules())


class Logging(BaseSettings):
    filename: str = Field(default="financial_news.logs")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class MServiceHeaders(BaseSettings):
    X_API_KEY: str = Field(..., env='X_API_KEY')
    X_SECRET_TOKEN: str = Field(..., env='X_SECRET_TOKEN')
    X_RAPID_KEY: str = Field(..., env='X_RAPID_KEY')

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class RSSFeedSettings(BaseSettings):
    RSS_FEED_URI: str = Field(..., env="RSS_FEED_URI")

    def uri_list(self) -> list[str]:
        return [self.RSS_FEED_URI]

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class GatewaySettings(BaseSettings):
    EXCHANGES_ENDPOINT: str = Field(..., env="EXCHANGES_ENDPOINT")
    EXCHANGE_STOCK_ENDPOINT: str = Field(..., env="EXCHANGE_STOCK_ENDPOINT")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class APPSettings(BaseSettings):
    """APP Confi settings"""
    APP_NAME: str = Field(default="Financial-News-Parser")
    TITLE: str = Field(default="Financial News API - Article Scrapper Micro Service")
    DESCRIPTION: str = Field(default="Financial News API Scrapper")
    VERSION: str = Field(default="1.0.0")
    TERMS: str = Field(default="https://eod-stock-api.site/terms")
    CONTACT_NAME: str = Field(default="MJ API Development")
    CONTACT_URL: str = Field(default="https://eod-stock-api.site/contact")
    CONTACT_EMAIL: str = Field(default="info@eod-stock-api.site")
    LICENSE_NAME: str = Field(default="Apache 2.0")
    LICENSE_URL: str = Field(default="https://www.apache.org/licenses/LICENSE-2.0.html")
    DOCS_URL: str = Field(default='/docs')
    OPENAPI_URL: str = Field(default='/openapi')
    REDOC_URL: str = Field(default='/redoc')


class CloudflareSettings(BaseSettings):
    CLOUDFLARE_ZONE_ID: str = Field(..., env="CLOUDFLARE_ZONE_ID")
    CLOUD_FLARE_API_KEY: str = Field(..., env="CLOUD_FLARE_API_KEY")
    CLOUD_FLARE_EMAIL: str = Field(..., env="CLOUD_FLARE_EMAIL")
    CLOUDFLARE_WORKER_NAME: str = Field(default="proxytask")

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


class ConfigInstance(BaseSettings):
    """
    **ConfigInstance**
        Main Config Settings
    """
    EOD_STOCK_API_KEY: str = Field(..., env='EOD_STOCK_API_KEY')
    DEVELOPMENT_SERVER_NAME: str = Field(..., env='DEVELOPMENT_SERVER_NAME')
    DATABASE_SETTINGS: DatabaseSettings = DatabaseSettings()
    SERVICE_HEADERS: MServiceHeaders = MServiceHeaders()
    RSS_FEEDS: RSSFeedSettings = RSSFeedSettings()
    LOGGING: Logging = Logging()
    CRON_ENDPOINT: str = Field(default="CRON_ENDPOINT")
    MEME_TICKERS_URI: str = Field(..., env="MEME_TICKERS_URI")
    GATEWAY_API: GatewaySettings = GatewaySettings()
    APP_SETTINGS: APPSettings = APPSettings()
    CLOUDFLARE_SETTINGS: CloudflareSettings = CloudflareSettings()
    DEBUG: bool = Field(default=False)

    class Config:
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


scheduler_settings = SchedulerSettings()


@lru_cache(maxsize=1, typed=True)
def config_instance() -> ConfigInstance:
    return ConfigInstance()
