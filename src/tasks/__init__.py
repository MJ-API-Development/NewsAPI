"""
Helper functions to obtain ticker symbols
    utils for searching through articles

"""
import asyncio
import requests
import feedparser
import aiohttp
from requests_cache import CachedSession

from models import Exchange, Stock
from src.models import Stock, RssArticle
from src.config import confing_instance
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

request_session = CachedSession('finance_news.cache', use_cache_dir=True,
                                cache_control=False,
                                # Use Cache-Control response headers for expiration, if available
                                expire_after=timedelta(hours=3),
                                # Otherwise expire responses after one day
                                allowable_codes=[200, 400],
                                # Cache 400 responses as a solemn reminder of your failures
                                allowable_methods=['GET', 'POST'],
                                # Cache whatever HTTP methods you want
                                ignored_parameters=['api_key'],
                                # Don't match this request param, and redact if from the cache
                                match_headers=['Accept-Language'],
                                # Cache a different response per language
                                stale_if_error=True,
                                # In case of request errors, use stale cache data if possible
                                )


async def get_exchange_tickers(exchange_code: str) -> list[Stock]:
    """
    **get_exchange_tickers**
        obtains a list of stocks for a given exchange

    :param exchange_code:
    :return:
    """
    url: str = f'https://gateway.eod-stock-api.site/api/v1/stocks/exchange/code/{exchange_code}'
    params: dict = dict(api_key=confing_instance.EOD_STOCK_API_KEY)

    response = request_session.get(url=url, params=params)
    response.raise_for_status()

    if response.headers.get('Content-Type') == 'application/json':
        response_data: dict[str, str | bool | dict[str, str]] = response.json()
        if response_data.get('status', False):
            stocks_list: list[dict[str, str]] = response_data.get('payload')

            return [Stock(**stock) for stock in stocks_list]

    return []


async def get_exchange_lists() -> list[Exchange]:
    """
        **get_exchange_lists**
            returns a list of exchanges from the Main API
    :return:
    """
    url: str = f'https://gateway.eod-stock-api.site/api/v1/exchanges'
    params: dict = dict(api_key=confing_instance.EOD_STOCK_API_KEY)

    response: requests.Response = request_session.get(url=url, params=params)
    response.raise_for_status()

    if response.headers.get('Content-Type') == 'application/json':
        response_data: dict[str, str | bool | dict[str, str]] = response.json()
        if response_data.get('status', False):
            exchange_list: list[dict[str, str]] = response_data.get('payload')

            return [Exchange(**exchange) for exchange in exchange_list]
    return []


async def parse_google_feeds(rss_url: str) -> list[RssArticle]:
    """
        **parse_google_feeds**
            will parse google rss feeds for specific subject articles
<id>tag:google.com,2005:reader/user/00244493797674210195/state/com.google/alerts/1129709253388904655</id>
<title>Google Alert - Financial News</title>
<link href="https://www.google.com/alerts/feeds/00244493797674210195/1129709253388904655" rel="self"/>
<updated>2023-04-15T12:50:23Z</updated>

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        summary = entry.summary
        published = entry.updated


    :param rss_url:
    :return: 
    """
    #  downloading Feed from source
    feed = feedparser.parse(rss_url)
    #  Creating RssArticles List
    articles_list = []
    for entry in feed.entries:
        article_entry = dict(title=entry.title, link=entry.link, published=entry.updated)
        articles_list.append(RssArticle(**article_entry))

    return articles_list


async def do_soup(html) -> tuple[str, str]:
    """
        parse the whole document and return formatted text
    :param html:
    :return:
    """
    soup = BeautifulSoup(html, 'html.parser')
    paragraphs = soup.find_all('p')
    return paragraphs[0], '\n\n'.join([p.get_text() for p in paragraphs])


async def download_article(link: str, timeout: int, headers: dict[str, str]) -> tuple[str, str] | tuple[None, str]:
    """
    **download_article**
        Download the article from the link stored in news_sentiment.link,
        then store the results in news_sentiment.article
    """
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=link, timeout=timeout) as response:
                response.raise_for_status()
                text: str = await response.text()
                return text
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return None
