import aiohttp
from src.models import NewsArticle
import asyncio
from src.config import config_instance
from src.utils import camel_to_snake
from src.utils.my_logger import init_logger


class DataConnector:
    """
        The Data Connector Keeps the articles in memory after reaching a certain thresh hold the articles
        are sent to the backend via CRON API.

        TODO - Feature Version must use Redis as a Message broker to store & send articles.
    """

    # noinspection PyUnusedLocal
    def __init__(self, *args, **kwargs):
        self.database_connector = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.database_buffer: list[NewsArticle] | None = None
        self._buffer_max_size: int = 100
        self.create_article_endpoint: str = f'{config_instance().CRON_ENDPOINT}/api/v1/news/article'
        self.aio_session: aiohttp.ClientSession = aiohttp.ClientSession(headers=create_auth_headers())
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

    async def incoming_articles(self, article_list: list[NewsArticle]):
        """
        **incoming_articles**
            :param article_list:
            :return:
        """
        self._logger.info(f"incoming articles Total : {len(article_list)}")
        async with self.lock:
            for article in article_list:
                if article:
                    self.database_buffer.append(article)
            self._logger.info(f"Done sending articles to the Data Connector")

    async def mem_store_to_storage(self):
        """
            **mem_store_to_storage**
                will store articles in memory when articles buffer is full will send the articles to the backend
                via EOD Stock  CRON API
        :return:
        """
        while True:
            # This sends the articles to database through a cron api

            if self.database_buffer:
                async with self.lock:
                    self._logger.info(f"Will attempt sending {len(self.database_buffer)} Articles to the Cron API")
                    create_article_tasks = [self.send_article_to_cron(article=article) for article in self.database_buffer if article]
                    self.database_buffer = []

                _ = await asyncio.gather(*create_article_tasks)

            else:
                self._logger.info(f"There is no articles to send to the CRON API")

            await asyncio.sleep(delay=900)

    async def send_article_to_cron(self, article: NewsArticle):
        """
            **send_article_to_cron**
                send articles via http to cron jobs server
        :param article:
        :return:
        """
        async with self.aio_session as session:
            return await session.post(url=self.create_article_endpoint, data=article.json())


def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }
