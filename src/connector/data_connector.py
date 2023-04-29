from typing import Coroutine

import aiohttp

from src.exceptions import RequestError
from src.models import NewsArticle
import asyncio
from src.config import config_instance
from src.utils import camel_to_snake
from src.utils.my_logger import init_logger
from src.telemetry import capture_telemetry


class DataConnector:
    """
    **DataConnector**

        The Data Connector Keeps the articles in memory after reaching a certain thresh hold the articles
        are sent to the backend via CRON API.
    """

    # noinspection PyUnusedLocal
    def __init__(self, *args, **kwargs):
        self.lock: asyncio.Lock = asyncio.Lock()
        self.mem_buffer: list[NewsArticle] | None = []
        self.create_article_endpoint: str = f'{config_instance().CRON_ENDPOINT}/api/v1/news/article'
        self.aio_session: aiohttp.ClientSession = aiohttp.ClientSession(headers=create_auth_headers())
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

    async def incoming_articles(self, article_list: list[NewsArticle]):
        """
        **incoming_articles**
            :param article_list:
            :return:
        """
        if not article_list:
            return

        self._logger.info(f"incoming articles Total : {len(article_list)}")
        async with self.lock:
            for article in article_list:
                if article:
                    self.mem_buffer.append(article)
            self._logger.info(f"Done sending articles to the Data Connector")

    @capture_telemetry(name='mem_store-to-storage')
    async def mem_store_to_storage(self):
        """
            **mem_store_to_storage**
                will store articles in memory when articles buffer is full will send the articles to the backend
                via EOD Stock  CRON API
        :return:
        """
        while True:
            # This sends the articles to database through a cron api

            if self.mem_buffer:
                async with self.lock:
                    self._logger.info(f"Will attempt sending {len(self.mem_buffer)} Articles to the Cron API")
                    create_article_tasks: list[Coroutine] = [self.send_article_to_cron(article=article)
                                                             for article in self.mem_buffer if article]
                    self.mem_buffer: list = []

                _ = await asyncio.gather(*create_article_tasks)

            else:
                self._logger.info(f"There is no articles to send to the CRON API")

            await asyncio.sleep(delay=90)

    @capture_telemetry(name='send-article-to-cron')
    async def send_article_to_cron(self, article: NewsArticle):
        """
            **send_article_to_cron**
                send articles via http to cron jobs server
        :param article:
        :return:
        """
        async with aiohttp.ClientSession(headers=create_auth_headers()) as session:
            try:
                response = await session.post(url=self.create_article_endpoint, data=article)
                response.raise_for_status()
                if response.headers.get('Content-Type') == 'application/json':
                    response_data: dict[str, str | dict[str, str]] = response.json()

                    self._logger.info(f"sent article : response : {response_data.get('payload')}")
                    return response_data
                self._logger.error(f"Error sending article to database : {response.text}")
            except aiohttp.ClientError as e:
                self._logger.error(f"aiohttp.ClientError caught while sending article to database : {e}")
                raise RequestError()


def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }
