import asyncio
import itertools

from src.models import RssArticle
from src.tasks import parse_google_feeds
from src.config import config_instance
from telemetry import capture_latency

rss_lists: list[str] = config_instance().RSS_FEEDS.uri_list()


@capture_latency(name='parse_feeds')
async def parse_feeds() -> list[RssArticle]:
    """
        **parse_feeds**
            goes through Google feeds lists and then parse the articles
    """

    feeds_tasks = [parse_google_feeds(rss_url=rss_url) for rss_url in rss_lists]
    feeds_list = await asyncio.gather(*feeds_tasks)
    return list(itertools.chain(*feeds_list))
