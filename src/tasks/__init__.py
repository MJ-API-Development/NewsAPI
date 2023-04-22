"""
Helper functions to obtain ticker symbols
    utils for searching through articles

"""
import asyncio
import requests
import feedparser
import aiohttp
from requests_cache import CachedSession

from src.models import Exchange, Stock
from src.models import Stock, RssArticle
from src.config import config_instance
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
    params: dict = dict(api_key=config_instance.EOD_STOCK_API_KEY)

    response: requests.Response = request_session.get(url=url, params=params)
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
    params: dict = dict(api_key=config_instance.EOD_STOCK_API_KEY)

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
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None


async def convert_to_time(time_str: str) -> datetime.time:
    """
    Converts a string representing time to a datetime.time object.

    :param time_str: A string representing time in the format HH:MM:SS.
    :return: A datetime.time object representing the input time.
    :raises ValueError: If the input time string is invalid.
    """
    try:
        time_obj = datetime.strptime(time_str, '%H:%M').time()
    except ValueError as e:
        raise ValueError(f"Invalid time format: {e}")
    return time_obj


async def can_run_task(schedule_time: str, task_details) -> bool:
    """
    Returns True if the task can be executed based on the schedule time and task details.

    :param schedule_time: A string representing the scheduled time in the format HH:MM:SS.
    :param task_details: A dictionary containing details about the task, including a boolean field 'task_ran'.
    :return: True if the task can be executed, False otherwise.
    """
    current_time = datetime.now().time()
    schedule_time = await convert_to_time(schedule_time)

    # Calculate the difference between the schedule time and current time in minutes
    time_diff = abs(schedule_time.hour - current_time.hour) * 60 + abs(schedule_time.minute - current_time.minute)

    # Check if the time difference is less than or equal to 10 minutes and the task has not already run
    return time_diff <= 10 and not task_details.task_ran


async def get_meme_tickers(count: int = 100, offset: int = 0) -> dict[str, str]:
    """
    Returns a dictionary of ticker symbols and company names for Mexican stocks.
    :return: A dictionary of ticker symbols and company names for Mexican stocks.
    """
    url = f"https://finance.yahoo.com/most-active?count={count}&offset={offset}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (HTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    try:
        request_session.headers = headers
        response = request_session.get(url)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return dict()

    soup = BeautifulSoup(response.content, "html.parser")
    tickers = {}

    for row in soup.find_all("tbody")[0].find_all("tr"):
        cells = row.find_all("td")
        symbol = cells[0].text.strip()
        name = cells[1].text.strip()
        tickers[symbol] = name

    return tickers
