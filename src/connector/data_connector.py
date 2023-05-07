import asyncio
import itertools
import pickle
from typing import Coroutine, TypeAlias

import aiohttp

from src.config import config_instance
from src.models import NewsArticle
from src.models import RssArticle
from src.telemetry import capture_telemetry
from src.utils import camel_to_snake
from src.utils.my_logger import init_logger

sendArticleType: TypeAlias = Coroutine[RssArticle | NewsArticle, None, RssArticle | NewsArticle | None]


async def save_to_local_drive(article: NewsArticle | RssArticle):
    """
        **save_to_local_drive**
            will save articles that failed to be sent to the API to local hard drive as temporary storage
    :param article:
    :return:
    """
    pickled_article = pickle.dumps(article)
    # TODO- learn how to save pickled classes to storage - or use a package that has the functionality


class DataConnector:
    """
    **DataConnector**

        The Data Connector Keeps the articles in memory after reaching a certain thresh hold the articles
        are sent to the backend via CRON API.
    """

    # noinspection PyUnusedLocal
    def __init__(self, *args, **kwargs):
        self._articles_present: set[str] = set()
        self._to_storage_delay: int = 96
        self.lock: asyncio.Lock = asyncio.Lock()
        self.mem_buffer: list[NewsArticle | RssArticle] = []
        self.create_article_endpoint: str = f'{config_instance().CRON_ENDPOINT}/api/v1/news/article'
        self.aio_session: aiohttp.ClientSession = aiohttp.ClientSession(headers=create_auth_headers())
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))

    def init(self):
        """
            prepare package and restore saved files from storage
        :return:
        """
        pass

    async def incoming_articles(self, article_list: list[dict[str, list[NewsArticle | RssArticle]]]):
        """
        **incoming_articles**
            :param article_list:
            :return:
        """
        if not article_list:
            self._logger.info("articles not found")
            return

        # Destructuring articles
        extended_articles: list[list[NewsArticle | RssArticle]] = []
        for article_dict in article_list:
            extended_articles.extend(article_dict.values())

        self._logger.info(f"incoming article batches : {len(extended_articles)}")
        for article in list(itertools.chain(*extended_articles)):
            if article and article.uuid not in self._articles_present:
                self.mem_buffer.append(article)
                self._articles_present.add(article.uuid)

        self._logger.info(f"Done prepping articles batch for sending to storage")
        self._logger.info(f"Total Articles Prepped : {len(self.mem_buffer)}")

    @capture_telemetry(name='mem_store-to-storage')
    async def mem_store_to_storage(self):
        """
            **mem_store_to_storage**
                will store articles in memory when articles buffer is full will send the articles to the backend
                via EOD Stock  CRON API
        :return:
        """
        if self.mem_buffer:
            self._logger.info(f"Will attempt sending {len(self.mem_buffer)} Articles to the Cron API")
            initial_articles = len(self.mem_buffer)
            create_article_tasks: list[sendArticleType] = [self.send_article_to_storage(article=article)
                                                           for article in self.mem_buffer if article]
            self.mem_buffer = []

            articles_not_saved: list[RssArticle | NewsArticle | None] = await asyncio.gather(*create_article_tasks)
            articles_not_saved: list[RssArticle | NewsArticle] = [article for article in articles_not_saved
                                                                  if article is not None]

            self.mem_buffer = articles_not_saved
            self._logger.info(f"Sent {initial_articles - len(self.mem_buffer)} Articles to storage backend")
        else:
            self._logger.info(f"There is no articles to send to the CRON API")

            # await asyncio.sleep(delay=self._to_storage_delay)

    @capture_telemetry(name='send-article-to-storage')
    async def send_article_to_storage(self, article: RssArticle | NewsArticle) -> RssArticle | NewsArticle | None:
        """
            **send_article_to_storage**
                send articles via http to cron jobs server
        :param article:
        :return:
        """
        async with aiohttp.ClientSession(headers=create_auth_headers()) as session:
            try:
                response: aiohttp.ClientResponse = await session.post(url=self.create_article_endpoint,
                                                                      data=article.dict())
                response.raise_for_status()
                if response.headers.get('Content-Type') == 'application/json':
                    response_data: dict[str, str | dict[str, str]] = response.json()

                    self._logger.info(f"Sent article : response : {response_data.get('payload')}")
                    return None

                self._logger.error(f"Error sending article to database : {response.text}")
                return article

            except aiohttp.ClientError as e:
                self._logger.error(f"ClientError caught while sending article to database : {str(e)}")
                # NOTE:  return this article so it gets sent again

                await save_to_local_drive(article=article)
                return article

            except Exception as e:
                self._logger.error(f"Exception sending article to database : {str(e)}")
                return article


def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }
