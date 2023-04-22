import aiohttp
from src.models import NewsArticle
import asyncio
from src.config import config_instance


class DataConnector:
    """
        The Data Connector Keeps the articles in memory after reaching a certain thresh hold the articles
        are sent to the backend via CRON API.

        TODO - Feature Version must use Redis as a Message broker to store articles.
    """

    def __init__(self, *args, **kwargs):
        self.database_connector = None
        self.mem_storage = asyncio.Queue()
        self.database_buffer: list[NewsArticle] | None = None
        self._buffer_max_size: int = 100
        self.create_article_endpoint: str = f'{config_instance().CRON_ENDPOINT}/api/v1/news/article'
        self.aio_session = aiohttp.ClientSession(headers=create_auth_headers())

    async def incoming_article(self, article: NewsArticle):
        """
            **incoming_article**
                will store each incoming article to mem_storage Queue
        :param article:
        :return:
        """
        await self.mem_storage.put(article)

    async def incoming_articles(self, article_list: list[NewsArticle]):
        """
        **incoming_articles**
            :param article_list:
            :return:
        """
        await asyncio.gather(*[self.incoming_article(article=article) for article in article_list if article])
        return

    async def mem_store_to_storage(self):
        """
            **mem_store_to_storage**
                will store articles in memory when articles buffer is full will send the articles to the backend
                via EOD Stock  CRON API
        :return:
        """
        while True:
            if self.mem_storage.qsize() < self._buffer_max_size:
                self.database_buffer.append(await self.mem_storage.get())
            else:
                # This sends the articles to database through a cron api
                create_article_tasks = [self.send_article_to_cron(article=article) for article in self.database_buffer]
                create_articles = await asyncio.gather(*create_article_tasks)

                self.database_buffer = []

            await asyncio.sleep(delay=60)

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
