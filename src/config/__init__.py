





from pydantic import BaseSettings

class SchedulerSettings(BaseSettings):
    """
        keys are scheduled times, values are dicts
        which include the task name and a bool to indicate the task already ran

    """
    schedule_times: dict[str, dict[str, str]]


settings = SchedulerSettings()
