import asyncio
import itertools
import pickle
from typing import Coroutine, TypeAlias

import aiohttp
from sqlalchemy.exc import DataError, OperationalError, IntegrityError, PendingRollbackError

from src.models.sql.news import News, Thumbnails, RelatedTickers
from src.connector.data_instance import mysql_instance
from src.config import config_instance
from src.models import NewsArticle
from src.models import RssArticle
from src.telemetry import capture_telemetry
from src.utils import camel_to_snake, create_id
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


# noinspection PyBroadException
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
            return

        # Destructuring articles
        extended_articles: list[list[NewsArticle | RssArticle]] = []
        for article_dict in article_list:
            article_values = article_dict.values()
            extended_articles.extend(article_values)

        normalized_list = []
        for news_articles in extended_articles:
            articles, ticker = news_articles
            if isinstance(articles, list):
                normalized_list.extend(articles)

        self._logger.info(f"incoming article batches : {len(normalized_list)}")
        for article in normalized_list:
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
            # create_article_tasks: list[sendArticleType] = [self.send_article_to_storage(article=article)
            #                                                for article in self.mem_buffer if article]
            _ = await self.send_to_database(article_list=self.mem_buffer)
            self.mem_buffer = []
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
                # response.raise_for_status()
                if response.headers.get('Content-Type') == 'application/json':
                    response_data: dict[str, str | dict[str, str]] = await response.json()

                    self._logger.info(f"Sent article : response : {response_data.get('payload')}")
                    return None

                self._logger.error(f"Error sending article to database : {await response.text()}")
                return article

            except aiohttp.ClientError as e:
                self._logger.info(await response.text())
                self._logger.error(f"ClientError caught while sending article to database : {str(e)}")
                # NOTE:  return this article so it gets sent again

                await save_to_local_drive(article=article)
                return article

            except Exception as e:
                self._logger.error(f"Exception sending article to database : {str(e)}")
                return article

    async def send_to_database(self, article_list: list[RssArticle | NewsArticle]):
        """
            **send_to_database**

        :param article_list:
        :return:
        """
        with mysql_instance.get_session() as session:
            # process articles in groups of 20
            batch_size: int = 20 if len(article_list) > 20 else len(article_list)
            total_saved = 0
            for i in range(0, len(article_list), batch_size):

                batch_articles: list[RssArticle | NewsArticle] = article_list[i:i + batch_size]
                news_instance_tasks = [self.create_news_instance(article) for article in batch_articles]
                thumbnail_instance_tasks = [self.create_thumbnails_instance(article) for article in batch_articles]
                related_tickers_instance_tasks = [self.create_related_tickers(article) for article in batch_articles]

                news_instances = await asyncio.gather(*news_instance_tasks)
                thumbnail_instances = await asyncio.gather(*thumbnail_instance_tasks)
                related_tickers_instances = await asyncio.gather(*related_tickers_instance_tasks)
                error_occured = False
                for instance in news_instances:
                    try:
                        session.add(instance)
                    except (DataError, OperationalError, IntegrityError, PendingRollbackError) as e:
                        error_occured = True
                        self._logger.info(f"exception Occurred : {e}")
                        session.rollback()
                if not error_occured:
                    for thumbnail_list in thumbnail_instances:
                        for thumbnail in thumbnail_list:
                            try:
                                session.add(thumbnail)
                            except (DataError, OperationalError, IntegrityError, PendingRollbackError) as e:
                                self._logger.info(f"exception Occurred : {e}")
                                session.rollback()

                    for tickers_list in related_tickers_instances:
                        for ticker in tickers_list:
                            try:
                                session.add(ticker)
                            except (DataError, OperationalError, IntegrityError, PendingRollbackError) as e:
                                self._logger.info(f"exception Occurred : {e}")
                                session.rollback()
                    session.flush()

            self._logger.info(f"Overall Articles Saved : {total_saved}")

    async def create_news_instance(self, article: RssArticle | NewsArticle) -> News:
        """
        **create_news_instance**

        :param article:
        :return:
        """
        try:
            return News(uuid=article.uuid, title=article.title, publisher=article.publisher,
                        link=article.link, providerPublishTime=article.providerPublishTime,
                        _type=article.type)
        except Exception as e:
            self._logger.info(f"unable to create instance {str(e)}")
            return None


    async def create_thumbnails_instance(self, article: RssArticle | NewsArticle) -> Thumbnails:
        """
        **create_thumbnails_instance**


        :param article:
        :return:
        """
        try:
            return [Thumbnails(thumbnail_id=create_id(), uuid=article.uuid, url=thumb.get('url'),
                               width=thumb.get('width'), height=thumb.get('height'), tag=thumb.get('tag')) for thumb in
                    article.thumbnail]
        except Exception as e:
            self._logger.info(f"unable to create instance {str(e)}")
            return None


    async def create_related_tickers(self, article: RssArticle | NewsArticle) -> RelatedTickers:
        """

        :param article:
        :return:
        """
        try:
            return [RelatedTickers(uuid=article.uuid, ticker=ticker) for ticker in article.relatedTickers]
        except Exception as e:
            self._logger.info(f"unable to create instance {str(e)}")
            return None


def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }
