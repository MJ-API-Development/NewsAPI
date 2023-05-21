import asyncio
from typing import Callable, Coroutine, TypeAlias

from fastapi import FastAPI

from src.models import NewsArticle, RssArticle
from src.api_routes.admin import admin_router
from src.api_routes.telemetry import telemetry_router
from src.config import scheduler_settings, create_schedules, config_instance
from src.connector.data_connector import data_sink
from src.tasks import can_run_task, get_meme_tickers
from src.tasks.news_scraper import scrape_news_yahoo, alternate_news_sources
from src.telemetry import Telemetry
ONE_HOURS = 60*60 * 1
ONE_MINUTE = 60
settings = config_instance().APP_SETTINGS
app = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    terms_of_service=settings.TERMS,
    contact={
        "name": settings.CONTACT_NAME,
        "url": settings.CONTACT_URL,
        "email": settings.CONTACT_EMAIL
    },
    license_info={
        "name": settings.LICENSE_NAME,
        "url": settings.LICENSE_URL,
    },
    docs_url=settings.DOCS_URL,
    openapi_url=settings.OPENAPI_URL,
    redoc_url=settings.REDOC_URL
)
scraperType: TypeAlias = Coroutine[list[str], None, list[dict[str, NewsArticle | RssArticle]]]

tasks_lookup: dict[str, Callable[[list[str]], scraperType]] = {
    'scrape_news_yahoo': scrape_news_yahoo,
    'alternate_news_sources': alternate_news_sources,
}

telemetry: list[Telemetry] = []


async def scheduled_task() -> None:
    """
        **scheduled_task**
            startup tasks for running schedules
    :return:
    """
    meme_tickers: dict[str, str] = await get_meme_tickers()
    # this counter helps refresh the meme tickers every hour - its based on the wait time not run time
    while True:
        # Check if it's time to run the task
        tickers_list: list[str] = list({ticker for ticker in meme_tickers.keys()})

        for schedule_time, task_details in list(scheduler_settings.schedule_times.items()):

            # Select and Run task
            articles: list[dict[str, NewsArticle | RssArticle]] = await scrape_news_yahoo(tickers_list)
            print(f'RETURNING: {len(articles)} Articles to storage')
            # prepare articles and store them into a buffer for sending to backend
            await data_sink.incoming_articles(article_list=articles)
            # send article to storage via articles API in Stock-API
            await data_sink.mem_store_to_storage()
            # Mark task as completed by setting task_ran to True and then store back into scheduler
            task_details.task_ran = True
            scheduler_settings.schedule_times[schedule_time] = task_details
            # Sleep for 1 hour minutes
            await asyncio.sleep(ONE_HOURS)
            # sleep one minute then run again
            # await asyncio.sleep(ONE_MINUTE)

        # refresh meme tickers
        meme_tickers = await get_meme_tickers()

        # refresh schedules
        scheduler_settings.schedule_times = create_schedules()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())


########################################################################################################################
# ###############################  ADMIN ROUTERS  ######################################################################
########################################################################################################################

app.include_router(admin_router)
app.include_router(telemetry_router)
