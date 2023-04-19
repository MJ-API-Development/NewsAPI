from src.models import NewsArticle
import asyncio


class DataConnector:
    """
        will store articles in a database
    """

    def __init__(self, *args, **kwargs):
        self.database_connector = None
        self.mem_storage = asyncio.Queue()
        self.database_buffer: list[NewsArticle] | None = None
        self._buffer_max_size: int = 100
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

        :param article_list:
        :return:
        """
        await asyncio.gather(*[self.incoming_article(article=article) for article in article_list if article])

    async def mem_store_to_storage(self):
        """
        18
        :return:
        """
        while True:
            if self.mem_storage.qsize() < self._buffer_max_size:
                self.database_buffer.append(await self.mem_storage.get())
