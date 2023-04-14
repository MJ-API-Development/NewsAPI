import datetime
import asyncio

from fastapi import FastAPI

from src.config import settings
from src.tasks.news_scraper import scrape_news_yahoo, alternate_news_sources, get_news

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


async def convert_to_time(time_str: str) -> datetime.time:
    """
    Converts a string representing time to a datetime.time object.

    :param time_str: A string representing time in the format HH:MM:SS.
    :return: A datetime.time object representing the input time.
    :raises ValueError: If the input time string is invalid.
    """
    try:
        time_obj = datetime.datetime.strptime(time_str, '%H:%M').time()
    except ValueError as e:
        raise ValueError(f"Invalid time format: {e}")
    return time_obj


async def can_run_task(schedule_time: str, task_details) -> bool:
    """
    Returns True if the task can be executed based on the schedule time and task details.

    :param schedule_time: A string representing the scheduled time in the format HH:MM:SS.
    :param task_details: A dictionary containing details about the task, including a boolean field 'task_ran'.
    :return: True if the task can be executed, False otherwise.
    """
    current_time = datetime.datetime.now().time()
    schedule_time = await convert_to_time(schedule_time)

    # Calculate the difference between the schedule time and current time in minutes
    time_diff = abs(schedule_time.hour - current_time.hour) * 60 + abs(schedule_time.minute - current_time.minute)

    # Check if the time difference is less than or equal to 10 minutes and the task has not already run
    return time_diff <= 10 and not task_details.task_ran


tickers_list = ['AAPL', 'AMZN', 'GOOGL', 'TSLA', 'FB', 'NVDA', 'NFLX', 'MSFT', 'JPM', 'V', 'BAC', 'WMT', 'JNJ', 'PG',
                'KO', 'PEP', 'CSCO', 'INTC', 'ORCL', 'AMD']


async def scheduled_task():
    while True:
        # Check if it's time to run the task
        current_time = datetime.datetime.now().strftime("%H:%M")

        for schedule_time, task_details in list(settings.schedule_times.items()):
            if await can_run_task(schedule_time=schedule_time, task_details=task_details):
                # Run the task
                print(f"Running {task_details.name} task at {current_time}")

                await tasks_lookup[task_details.name](tickers_list)
                break

        # Sleep for 10 minute
        print("proceeding to wait")
        # await get_news(tickers_list)
        await asyncio.sleep(600)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())
