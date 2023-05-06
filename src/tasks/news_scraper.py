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


@capture_telemetry(name='scrape_news_yahoo')
async def scrape_news_yahoo(tickers: list[str]) -> list[dict[str, NewsArticle]]:
    """
    **scrape_news_yahoo**
    Scrapes financial articles from Yahoo Finance.

    :param tickers: A list of stock tickers to scrape news articles for.
    :return: A list of dictionaries containing ticker symbols as keys and a list of articles as values.
    """
    articles_tickers_tasks = [ticker_articles(ticker=ticker) for ticker in tickers]
    articles_tickers = await asyncio.gather(*articles_tickers_tasks)
    return [{ticker: article} for article, ticker in articles_tickers]


async def ticker_articles(ticker: str) -> tuple[NewsArticle, str]:
    """
        **ticker_articles**
            will return a list of articles for a single ticker
    :param ticker:
    :return:
    """
    _headers: dict[str, str] = await switch_headers()
    request_session.headers.update(_headers)
    ticker = yf.Ticker(ticker=ticker.upper(), session=request_session)
    news_data_list: list[dict[str, str | int | list[dict[str, str | int]]]] = ticker.news
    articles = []
    # resetting error count to 0
    cloud_flare_proxy.error_count = 0
    for article in news_data_list:
        if not isinstance(article, dict):
            continue

        article['thumbnail'] = article.get('thumbnail', {}).get('resolutions', []) \
            if 'thumbnail' in article and isinstance(article['thumbnail'], dict) else []
        _article: NewsArticle = NewsArticle(**article)

        title, summary, body, images = await parse_article(article=_article)
        # _res = [title, summary, body, images]
        if "not supported on your current browser version" not in summary:
            _article.summary = summary
        if "not supported on your current browser version" not in body:
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


@capture_telemetry(name='parse_article')
async def parse_article(article: RssArticle) -> tuple[str, str, str, list[dict[str, str | int]]]:
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
