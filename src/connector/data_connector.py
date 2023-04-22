import aiohttp
from src.models import NewsArticle
import asyncio
from src.config import config_instance


class DataConnector:
    """
        will store articles in a database
    """

    def __init__(self, *args, **kwargs):
        self.database_connector = None
        self.mem_storage = asyncio.Queue()
        self.database_buffer: list[NewsArticle] | None = None
        self._buffer_max_size: int = 100
        self.create_article_endpoint: str = f'{config_instance().CRON_ENDPOINT}/api/v1/news/article'
        pass

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
        18
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

    async def send_article_to_cron(self, article: NewsArticle):
        """
            **send_article_to_cron**
        :param article:
        :return:
        """
        headers = await create_auth_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            return await session.post(url=self.create_article_endpoint, data=article.json())


async def create_auth_headers():
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-API-KEY': config_instance().SERVICE_HEADERS.X_API_KEY,
        'X-SECRET-TOKEN': config_instance().SERVICE_HEADERS.X_SECRET_TOKEN,
        'X-RapidAPI-Proxy-Secret': config_instance().SERVICE_HEADERS.X_RAPID_KEY
    }
