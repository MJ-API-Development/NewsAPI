import datetime
import asyncio

from fastapi import FastAPI

from src.api_routes.articles import articles_router
from src.config import scheduler_settings
from src.tasks.news_scraper import scrape_news_yahoo, alternate_news_sources
from src.tasks import can_run_task, get_meme_tickers
from src.connector.data_connector import DataConnector

description = """Financial News API Scrapper"""

app = FastAPI(
    title="Financial News API - Article Scrapper Micro Service",
    description=description,
    version="1.0.0",
    terms_of_service="https://eod-stock-api.site/terms",
    contact={
        "name": "MJ API Development",
        "url": "https://eod-stock-api.site/contact",
        "email": "info@eod-stock-api.site"
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
    docs_url='/docs',
    openapi_url='/openapi',
    redoc_url='/redoc'
)

tasks_lookup = {
    'scrape_news_yahoo': scrape_news_yahoo,
    'alternate_news_sources': alternate_news_sources,
}

data_sink: DataConnector = DataConnector()


async def scheduled_task():
    """
        **scheduled_task**
    :return:
    """
    meme_tickers = await get_meme_tickers()
    can_refresh_count = 0

    while True:
        # Check if it's time to run the task
        current_time = datetime.datetime.now().strftime("%H:%M")
        tickers_list: list[str] = list({ticker for ticker in meme_tickers.keys()})
        can_refresh_count += 1
        for schedule_time, task_details in list(scheduler_settings.schedule_times.items()):
            if await can_run_task(schedule_time=schedule_time, task_details=task_details):
                # Run the task
                print(f"Running {task_details.name} task at {current_time}")

                articles = await tasks_lookup[task_details.name](tickers_list)
                # this will store the article to whatever storage data_sink is storing in
                asyncio.create_task(data_sink.incoming_articles(article_list=articles))

        # Sleep for 10 minute
        await asyncio.sleep(600)
        if can_refresh_count == 6:
            # will refresh meme tickers every hour
            meme_tickers = await get_meme_tickers()
            can_refresh_count = 0


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())
    asyncio.create_task(data_sink.mem_store_to_storage())

# TODO ADD Some Management API to router so the service worker can be controlled and its activity monitored from
#  the admin system
# app.include_router(articles_router)
