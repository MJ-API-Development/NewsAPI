import asyncio
import itertools
import json

from bs4 import BeautifulSoup

from src.connector.data_connector import data_sink
from src.exceptions import ErrorParsingHTMLDocument
from src.models import RssArticle, NewsArticle
from src.tasks import download_article
from src.tasks.rss_feeds import parse_feeds
from src.tasks.utils import switch_headers, cloud_flare_proxy
from src.telemetry import capture_telemetry
from src.utils.my_logger import init_logger

news_scrapper_logger = init_logger('news-scrapper-logger')


async def scrape_news_yahoo(tickers: list[str]) -> list[NewsArticle | RssArticle]:
    try:
        articles_tickers = []
        chunk_size = 10 if len(tickers) > 10 else len(tickers)

        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i + chunk_size]
            tasks = [ticker_articles(ticker=ticker) for ticker in chunk]
            results = await asyncio.gather(*tasks)
            articles_tickers.extend([articles for articles in results if articles is not None])

        return list(itertools.chain(*articles_tickers))
    except Exception as e:
        news_scrapper_logger.info(f"Exception raised: {str(e)}")
        return []


async def ticker_articles(ticker: str) -> list[NewsArticle | RssArticle]:
    """
        **ticker_articles**
            will return a list of articles for a single ticker
    :param ticker:
    :return:
    """
    # Yahoo finance query api
    url = f'https://query2.finance.yahoo.com/v1/finance/search?q={ticker}'
    try:
        response = await cloud_flare_proxy.make_request_with_cloudflare(url=url, method='GET')
        news_data_list: list[dict[str, str | int | list[dict[str, str | int]]]] = json.loads(response).get('news', [])
    except Exception as e:
        news_scrapper_logger.info(f'Ticker Articles Error: {str(e)}')
        return []

    articles = []

    # resetting error count to 0 - this means for every ticker to search the error count goes back to zero
    cloud_flare_proxy.error_count = 0
    for article in news_data_list:

        if not isinstance(article, dict):
            continue
        article['thumbnail'] = get_thumbnail_resolutions(article=article)
        # noinspection PyBroadException
        try:
            # NOTE: sometimes there is a strange list error here, don't know why honestly
            _article: NewsArticle | None = NewsArticle(**dict(article))
        except Exception as e:
            news_scrapper_logger.info(f'Error Creating NewsArticle: {str(e)}')
            _article = None

        if _article and await data_sink.article_not_saved(article=article):
            try:
                title, summary, body = await parse_article(article=_article)
                # Note: funny way of catching parser errors but hey - beggars cant be choosers
                if summary and ("not supported on your current browser version" not in summary.casefold()):
                    _article.summary = summary
                if body and ("not supported on your current browser version" not in body.casefold()):
                    _article.body = body

                articles.append(_article)

            except Exception as e:
                news_scrapper_logger.info(f'error parsing article: {str(e)}')

    return articles


def get_thumbnail_resolutions(article: dict[str, str, dict[str, str | int] | list]) -> list[dict[str, str | int]]:
    """Gets the thumbnail resolutions for an article.
  Args:
    article: The article to get the thumbnail resolutions for.
  Returns:
    A list of thumbnail resolutions.
  """
    thumbnail = article.get('thumbnail')
    if thumbnail is None:
        return []
    if not isinstance(thumbnail, dict):
        return []
    return thumbnail.get('resolutions', [])


# noinspection PyUnusedLocal
@capture_telemetry(name='alternate_news_sources')
async def alternate_news_sources(*args, **kwargs) -> list[NewsArticle| RssArticle]:
    """
        **alternate_news_sources**
            search for news from alternate sources
    :return:
    """
    articles_list: list[NewsArticle| RssArticle] = await parse_feeds()
    for i, article in enumerate(articles_list):
        try:
            title, summary, body = await parse_article(article)
        except TypeError:
            raise ErrorParsingHTMLDocument()
        # NOTE - probably nothing to lose sleep over, but if an article does not
        # have images it won't be saved
        if not all([summary, body]):
            continue

        _related_tickers = await find_related_tickers(article)
        article.body = body
        article.summary = summary
        article.title = title
        article.relatedTickers = _related_tickers
        articles_list[i] = article

    return articles_list


async def parse_article(article: RssArticle | NewsArticle | None) -> tuple[str | None, str | None, str | None]:
    """**parse_article**
    will parse articles from yfinance
    """
    if not article:
        return None, None, None

    _html = await cloud_flare_proxy.make_request_with_cloudflare(url=article.link, method="GET")
    _headers = await switch_headers()
    html = _html if _html is not None else await download_article(link=article.link, timeout=9600, headers=_headers)
    if html is None:
        return None, None, None
    try:
        soup = BeautifulSoup(html, 'html.parser')
        title: str = soup.find('h1').get_text() or soup.find('h2').get_text()
        summary: str = soup.find('p').get_text()
        body: str | None = None
        try:
            for elem in soup.find_all('p'):
                body += elem.get_text()
        except Exception as e:
            pass
        return title, summary, body
    except Exception:
        raise ErrorParsingHTMLDocument()


# noinspection PyUnusedLocal
async def find_related_tickers(article: RssArticle) -> list[str]:
    """
        **find_related_tickers**
            from the body of the article try learning what tickers could be related to the article
    :param article:
    :return:
    """
    return []
