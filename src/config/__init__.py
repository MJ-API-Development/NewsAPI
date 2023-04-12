





from pydantic import BaseSettings

class SchedulerSettings(BaseSettings):
    schedule_times: dict[str, str]


settings = SchedulerSettings()
