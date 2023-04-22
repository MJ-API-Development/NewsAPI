from functools import lru_cache

from pydantic import BaseModel, BaseSettings, Field


class Task(BaseModel):
    name: str
    task_ran: bool


def create_schedules() -> dict[str, dict[str, str | bool]]:
    """
        creates schedules to run news scrapping tasks and return them
        TODO - create a route to set the schedules
    :return:
    """
    tasks_schedules = {
        '00:00': Task(name='scrape_news_yahoo', task_ran=False),
        '03:00': Task(name='scrape_news_yahoo', task_ran=False),
        '06:00': Task(name='scrape_news_yahoo', task_ran=False),
        '09:00': Task(name='scrape_news_yahoo', task_ran=False),
        '12:00': Task(name='scrape_news_yahoo', task_ran=False),
        '15:00': Task(name='scrape_news_yahoo', task_ran=False),
        '18:00': Task(name='scrape_news_yahoo', task_ran=False),
        '21:00': Task(name='scrape_news_yahoo', task_ran=False),

        '01:30': Task(name='alternate_news_sources', task_ran=False),
        '04:30': Task(name='alternate_news_sources', task_ran=False),
        '07:30': Task(name='alternate_news_sources', task_ran=False),
        '10:30': Task(name='alternate_news_sources', task_ran=False),
        '13:30': Task(name='alternate_news_sources', task_ran=False),
        '16:30': Task(name='alternate_news_sources', task_ran=False),
        '19:30': Task(name='alternate_news_sources', task_ran=False),
        '22:30': Task(name='alternate_news_sources', task_ran=False)
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


class ConfigInstance(BaseSettings):
    APP_NAME: str = Field(default="Financial-News-Parser")
    EOD_STOCK_API_KEY: str = Field(..., env='EOD_STOCK_API_KEY')
    DEVELOPMENT_SERVER_NAME: str = Field(..., env='DEVELOPMENT')
    DATABASE_SETTINGS: DatabaseSettings = DatabaseSettings()
    SERVICE_HEADERS: MServiceHeaders = MServiceHeaders()
    LOGGING: Logging = Logging()
    CRON_ENDPOINT: str = Field(default="https://cron.eod-stock-api.site")

    class Config:
        """configuration file for admin scheduler_settings"""
        env_file = '.env.development'
        env_file_encoding = 'utf-8'


scheduler_settings = SchedulerSettings()


@lru_cache(maxsize=1, typed=True)
def config_instance() -> ConfigInstance:
    return ConfigInstance()
