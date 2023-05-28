import asyncio
import pickle
from typing import Coroutine, TypeAlias

import aiohttp

from src.config import config_instance
from src.connector.data_instance import mysql_instance
from src.models import NewsArticle
from src.models import RssArticle
from src.models.sql.news import News, Thumbnails, RelatedTickers, NewsSentiment
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
    _ = pickle.dumps(article)
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

    async def article_not_saved(self, article: dict) -> bool:
        return isinstance(article, dict) and (article.get('uuid', "1234") not in self._articles_present)

    async def incoming_articles(self, article_list: list[NewsArticle | RssArticle]):
        """
        **incoming_articles**
            :param article_list:
            :return:
        """
        if not article_list:
            return

        # Destructuring articles
        # extended_articles = [article_dict.values() for article_dict in article_list if article_dict is not None]
        #
        # normalized_list = []
        # for news_articles in extended_articles:
        #     articles, ticker = news_articles
        #     if isinstance(articles, list):
        #         normalized_list.extend(articles)
        #
        # self._logger.info(f"Incoming Article Batches : {len(normalized_list)}")
        #
        for article in article_list:
            if article and str(article.uuid) not in self._articles_present:
                self.mem_buffer.append(article)
                self._articles_present.add(str(article.uuid))

        self._logger.info(f"Done prepping articles batch for sending to storage")
        self._logger.info(f"Total Articles Prepped : {len(self.mem_buffer)}")

    async def mem_store_to_storage(self):
        """
            **mem_store_to_storage**
                will store articles in memory when articles buffer is full will send the articles to the backend
                via EOD Stock  CRON API
        :return:
        """
        if self.mem_buffer:
            initial_articles = len(self.mem_buffer)
            self._logger.info(f"Will attempt sending {initial_articles} Articles to the Cron API")
            # create_article_tasks: list[sendArticleType] = [self.send_article_to_storage(article=article)
            #                                                for article in self.mem_buffer if article]
            _ = await self.send_to_database()
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

    async def send_to_database(self):
        """
            **send_to_database**
        :return:
        """
        with mysql_instance.get_session() as session:
            # process articles in groups of 20
            batch_size: int = 20 if len(self.mem_buffer) > 20 else len(self.mem_buffer)
            total_saved = 0

            for i in range(0, len(self.mem_buffer), batch_size):
                batch_articles: list[RssArticle | NewsArticle] = self.mem_buffer[i:i + batch_size]
                news_instances = await asyncio.gather(*[self.create_news_instance(article)
                                                        for article in batch_articles])
                sentiment_instances = await asyncio.gather(*[self.create_news_sentiment(article)
                                                             for article in batch_articles])
                thumbnail_instances = await asyncio.gather(*[self.create_thumbnails_instance(article)
                                                             for article in batch_articles])
                related_tickers_instances = await asyncio.gather(*[self.create_related_tickers(article)
                                                                   for article in batch_articles])
                total_saved += batch_size
                for instance in news_instances:
                    try:
                        session.add(instance)
                    except Exception:
                        self._logger.info(f"Exception Occurred When adding News Article")

                for news_sentiment in sentiment_instances:
                    try:
                        session.add(news_sentiment)
                    except Exception:
                        self._logger.info(f"Exception Occurred When adding News Sentiment")

                for thumbnail_list in thumbnail_instances:
                    for thumbnail in thumbnail_list:
                        try:
                            session.add(thumbnail)
                        except Exception:
                            self._logger.info(f"Exception Occurred when Adding Thumbnails")

                for tickers_list in related_tickers_instances:
                    for ticker in tickers_list:
                        try:
                            session.add(ticker)
                        except Exception:
                            self._logger.info(f"Exception Occurred when adding Tickers")

                self._logger.info(f"Batch Count : {i}")
            try:
                session.flush()
            except Exception as e:
                self._logger.info(f"Exception Occurred When Flushing")
                self._logger.info(str(e))

            self._logger.info(f"Overall Articles Saved : {total_saved}")

    async def create_news_instance(self, article: RssArticle | NewsArticle) -> News | None:
        """
        **create_news_instance**

        :param article:
        :return:
        """
        try:
            return News(uuid=str(article.uuid), title=article.title, publisher=article.publisher,
                        link=article.link, providerPublishTime=article.providerPublishTime,
                        _type=article.type)
        except Exception:
            self._logger.info(f"Unable to create instance News Article")
            return None

    async def create_news_sentiment(self, article: RssArticle | NewsArticle) -> NewsSentiment | None:
        """

        :param article:
        :return:
        """
        try:
            return NewsSentiment(article_uuid=article.uuid, stock_codes=",".join(article.relatedTickers),
                                 title=article.title, link=article.link, article=article.body,
                                 article_tldr=article.summary)
        except Exception:
            self._logger.info(f"Unable to create instance Sentiment Model")
            return None

    async def create_thumbnails_instance(self, article: RssArticle | NewsArticle) -> list[Thumbnails] | None:
        """
        **create_thumbnails_instance**


        :param article:
        :return:
        """
        try:
            return [Thumbnails(thumbnail_id=create_id(), uuid=str(article.uuid), url=thumb.get('url'),
                               width=thumb.get('width'), height=thumb.get('height'), tag=thumb.get('tag')) for thumb in
                    article.thumbnail]
        except Exception:
            self._logger.info(f"Unable to create instance Thumbnail Model")
            return None

    async def create_related_tickers(self, article: RssArticle | NewsArticle) -> list[RelatedTickers] | None:
        """
        :param article:
        :return:
        """
        try:
            return [RelatedTickers(uuid=str(article.uuid), ticker=ticker) for ticker in article.relatedTickers]
        except Exception:
            self._logger.info(f"Unable to create Related Tickers Model")
            return None


def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }


data_sink: DataConnector = DataConnector()
