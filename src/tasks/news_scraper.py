import asyncio

import yfinance as yf
from bs4 import BeautifulSoup

from src.exceptions import ErrorParsingHTMLDocument
from src.models import RssArticle, NewsArticle
from src.tasks import request_session, download_article
from src.tasks.rss_feeds import parse_feeds
from src.tasks.utils import switch_headers, cloud_flare_proxy
from src.telemetry import capture_telemetry
from src.utils.my_logger import init_logger

news_scrapper_logger = init_logger('news-scrapper-logger')


async def scrape_news_yahoo(tickers: list[str]) -> list[dict[str, list[NewsArticle | RssArticle]]]:
    try:
        articles_tickers = []
        chunk_size = 10
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i+chunk_size]
            tasks = [ticker_articles(ticker=ticker) for ticker in chunk]
            results = await asyncio.gather(*tasks)
            for articles, ticker in zip(results, chunk):
                if articles:
                    articles_tickers.append({ticker: articles})
            await asyncio.sleep(30)

        return articles_tickers
    except Exception as e:
        print(f"Exception raised: {e}")
        return []


async def ticker_articles(ticker: str) -> tuple[list[NewsArticle], str]:
    """
        **ticker_articles**
            will return a list of articles for a single ticker
    :param ticker:
    :return:
    """
    _headers: dict[str, str] = await switch_headers()
    request_session.headers.update(_headers)

    # noinspection PyBroadException
    try:
        ticker = yf.Ticker(ticker=ticker.upper(), session=request_session)
        news_data_list: list[dict[str, str | int | list[dict[str, str | int]]]] = ticker.news
    except Exception as e:
        news_scrapper_logger.info(f'ticker articles error: {str(e)}')
        return [], ticker

    articles = []

    # resetting error count to 0 - this means for every ticker to search the error count goes back to zero
    cloud_flare_proxy.error_count = 0
    for article in news_data_list:

        if not isinstance(article, dict):
            continue

        article['thumbnail'] = article.get('thumbnail', {}).get('resolutions', []) \
            if 'thumbnail' in article and isinstance(article['thumbnail'], dict) else []

        # noinspection PyBroadException
        try:
            # NOTE: sometimes there is a strange list error here, don't know why honestly
            _article: NewsArticle = NewsArticle(**article)
        except Exception as e:
            news_scrapper_logger.info(f'error parsing article: {str(e)}')
            continue

        title, summary, body, images = await parse_article(article=_article)

        # Note: funny way of catching parser errors but hey - beggars cant be choosers
        if "not supported on your current browser version" not in summary.casefold():
            _article.summary = summary
        if "not supported on your current browser version" not in body.casefold():
            _article.body = body

        articles.append(_article)
    return articles, ticker


# noinspection PyUnusedLocal
@capture_telemetry(name='alternate_news_sources')
async def alternate_news_sources(*args, **kwargs) -> list[dict[str, RssArticle]]:
    """
        **alternate_news_sources**
            search for news from alternate sources
    :return:
    """
    articles_list: list[RssArticle] = await parse_feeds()
    news = []
    for i, article in enumerate(articles_list):
        try:
            title, summary, body, images = await parse_article(article)
        except TypeError:
            raise ErrorParsingHTMLDocument()
        # NOTE - probably nothing to lose sleep over, but if an article does not
        # have images it won't be saved
        if not all([summary, body, images]):
            continue

        _related_tickers = await find_related_tickers(article)
        article.body = body
        article.summary = summary
        article.thumbnail = images
        article.title = title
        article.relatedTickers = _related_tickers
        articles_list[i] = article

    news.append({'alt': articles_list})
    return news


async def parse_article(article: RssArticle) -> tuple[str | None, str | None, str | None, list[dict[str, str | int]]]:
    """**parse_article**
    will parse articles from yfinance
    """
    if not article:
        return None, None, None, []

    _html = await cloud_flare_proxy.make_request_with_cloudflare(url=article.link, method="GET")
    _headers = await switch_headers()
    html = _html if _html is not None else await download_article(link=article.link, timeout=9600, headers=_headers)
    if html is None:
        return None, None, None, []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        title: str = soup.find('h1').get_text()
        summary: str = soup.find('p').get_text()
        body: str = ''
        images: list[dict[str, str | int]] = []
        for elem in soup.select('div.article-content > *'):
            if elem.name == 'h1':
                title = elem.get_text()
            if elem.name == 'p':
                body += elem.get_text()
            elif elem.name == 'img':
                images.append(dict(src=elem['src'], alt=elem['alt'], width=elem['width'], height=elem['height']))
        return title, summary, body, images
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
