import asyncio

from fastapi import FastAPI

from src.api_routes.admin import admin_router
from src.api_routes.telemetry import telemetry_router
from src.config import scheduler_settings, create_schedules, config_instance
from src.connector.data_connector import DataConnector
from src.tasks import can_run_task, get_meme_tickers
from src.tasks.news_scraper import scrape_news_yahoo, alternate_news_sources
from src.telemetry import Telemetry


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

tasks_lookup = {
    'scrape_news_yahoo': scrape_news_yahoo,
    'alternate_news_sources': alternate_news_sources,
}

data_sink: DataConnector = DataConnector()

telemetry: list[Telemetry] = []


async def scheduled_task() -> None:
    """
        **scheduled_task**
            startup tasks for running schedules
    :return:
    """
    meme_tickers: dict[str, str] = await get_meme_tickers()
    # this counter helps refresh the meme tickers every hour - its based on the wait time not run time
    can_refresh_count: int = 0
    _run_counter: int = 0
    while True:
        # Check if it's time to run the task
        tickers_list: list[str] = list({ticker for ticker in meme_tickers.keys()})
        can_refresh_count += 1

        for schedule_time, task_details in list(scheduler_settings.schedule_times.items()):
            if await can_run_task(schedule_time=schedule_time, task_details=task_details):
                # Run the task
                articles = await tasks_lookup[task_details.name](tickers_list)
                scheduler_settings.schedule_times[schedule_time] = task_details.task_ran
                # this will store the article to whatever storage data_sink is storing in
                asyncio.create_task(data_sink.incoming_articles(article_list=articles))
                continue

        # Sleep for 10 minute
        await asyncio.sleep(600)
        # will refresh the tickers in 3 hours - cache lasts until then
        if can_refresh_count == 6*3:
            # will refresh meme tickers every hour
            meme_tickers = await get_meme_tickers()
            can_refresh_count = 0

        if _run_counter == len(scheduler_settings.schedule_times.items()):
            # once the scheduler is exhausted this will create a new schedule for the day
            scheduler_settings.schedule_times = create_schedules()
            _run_counter = 0
        _run_counter += 1


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())
    asyncio.create_task(data_sink.mem_store_to_storage())


########################################################################################################################
# ###############################  ADMIN ROUTERS  ######################################################################
########################################################################################################################

app.include_router(admin_router)
app.include_router(telemetry_router)
