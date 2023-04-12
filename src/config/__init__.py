
from pydantic import BaseSettings, Field



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
        '00:00': Task(task='scrape_news_yahoo', task_ran=False),
        '03:00': Task(name='scrape_news_yahoo', task_ran=False),
        '06:00': Task(name='scrape_news_yahoo', task_ran=False),
        '09:00': Task(name='scrape_news_yahoo', task_ran=False),
        '12:00': Task(name='scrape_news_yahoo', task_ran=False),
        '15:00': Taskdict(name='scrape_news_yahoo', task_ran=False),
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


class SchedulerSettings(BaseSettings):
    """
        keys are scheduled times, values are dicts
        which include the task name and a bool to indicate the task already ran

    """
    schedule_times: dict[str, Task] = Field(default_factory=lambda:create_schedules())


settings = SchedulerSettings()
