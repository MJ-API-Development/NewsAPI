import datetime
import asyncio

from fastapi import FastAPI

from src.config import settings
from src.tasks.news_scraper import scrape_news_yahoo, alternate_news_sources
from src.tasks import can_run_task, get_meme_tickers

description = """ News API Scrapper"""

app = FastAPI(
    title="Financial News API",
    description=description,
    version="1.0.0",
    terms_of_service="https://eod-stock-api.site/terms",
    contact={
        "name": "Financial News API",
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
        tickers_list: list[str] = list(set([ticker for ticker in meme_tickers.keys()]))
        can_refresh_count += 1
        for schedule_time, task_details in list(settings.schedule_times.items()):
            if await can_run_task(schedule_time=schedule_time, task_details=task_details):
                # Run the task
                print(f"Running {task_details.name} task at {current_time}")

                await tasks_lookup[task_details.name](tickers_list)
                break

        # Sleep for 10 minute
        await asyncio.sleep(600)
        if can_refresh_count == 6:
            # will refresh meme tickers every hour
            meme_tickers = await get_meme_tickers()
            can_refresh_count = 0


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())
