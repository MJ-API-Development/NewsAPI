
import asyncio
import itertools

from src.models import RssArticle
from src.tasks import parse_google_feeds

rss_lists = [
    'https://www.google.com/alerts/feeds/00244493797674210195/1129709253388904655'
]


async def parse_feeds() -> list[RssArticle]:

    """
        **parse_feeds**
            goes through google feeds lists and then parse the articles
    """

    feeds_tasks = [parse_google_feeds(rss_url=rss_url) for rss_url in rss_lists]
    feeds_list = asyncio.gather(*feeds_tasks)
    return list(itertools.chain(*feeds_list))
