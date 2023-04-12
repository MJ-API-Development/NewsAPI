
from fastapi import FastAPI
from src.config import settings


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


async def scheduled_task():
    while True:
        # Check if it's time to run the task
        current_time = datetime.now().strftime("%H:%M")
        for task_name, schedule_time in settings.schedule_times.items():
            if current_time >= schedule_time:
                # Run the task
                print(f"Running {task_name} task at {current_time}")
                # TODO: Add your task implementation here


        # Sleep for 1 minute
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_task())

