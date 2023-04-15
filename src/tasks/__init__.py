

"""
    utils for searching through articles

"""
import requests
import feedparser

from models import Exchange, Stock
from src.models import Stock, RssArticle
from src.config import confing_instance


async def get_exchange_tickers(exchange_code: str) -> list[Stock]:
    """
    **get_exchange_tickers**
        obtains a list of stocks for a given exchange

    :param exchange_code:
    :return:
    """
    url: str = f'https://gateway.eod-stock-api.site/api/v1/stocks/exchange/code/{exchange_code}'
    params: dict = dict(api_key=confing_instance.EOD_STOCK_API_KEY)

    with requests.Session() as session:

        response = session.get(url=url, params=params)
        response.raise_for_status()

        if response.headers.get('Content-Type') == 'application/json':
            response_data: dict[str, str | bool | dict[str, str]] = response.json()
            if response_data.get('status', False):
                stocks_list: list[dict[str, str]] = response_data.get('payload')

                return [Stock(**stock) for stock in stocks_list]

        return []


async def get_exchange_lists() -> list[Exchange]:
    """

    :return:
    """
    url: str = f'https://gateway.eod-stock-api.site/api/v1/exchanges'
    params: dict = dict(api_key=confing_instance.EOD_STOCK_API_KEY)

    with requests.Session() as session:
        response: requests.Response = session.get(url=url, params=params)
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

    for entry in feed.entries:
        title = entry.title
        link = entry.link
        summary = entry.summary
        published = entry.published


    :param rss_url:
    :return: 
    """
    #  downloading Feed from source
    feed = feedparser.parse(rss_url)
    #  Creating RssArticles List
    return [RssArticle(entry) for entry in feed.entries]


