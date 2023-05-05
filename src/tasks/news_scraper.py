import random
import yfinance as yf
from bs4 import BeautifulSoup

from src.exceptions import ErrorParsingHTMLDocument
from src.models import RssArticle, NewsArticle
from src.tasks.rss_feeds import parse_feeds
from src.tasks import download_article, request_session
from src.telemetry import capture_telemetry
from src.utils.my_logger import init_logger

news_scrapper_logger = init_logger('news-scrapper-logger')


async def switch_headers() -> dict[str, str]:
    """
        this method is used to select a random header to use in parsing news
    :return:
    """
    return random.choice([
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:55.0) Gecko/20100101 Firefox/55.0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/40.15063.0.0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
        }
    ])


@capture_telemetry(name='scrape_news_yahoo')
async def scrape_news_yahoo(tickers: list[str]) -> list[dict[str, NewsArticle]]:
    """
    **scrape_news_yahoo**
    Scrapes financial articles from Yahoo Finance.

    :param tickers: A list of stock tickers to scrape news articles for.
    :return: A list of dictionaries containing ticker symbols as keys and a list of articles as values.
    """
    news = []
    _headers: dict[str, str] = await switch_headers()
    request_session.headers.update(_headers)

    for ticker in tickers:
        ticker = yf.Ticker(ticker=ticker.upper(), session=request_session)
        news_data_list: list[dict[str, str | int | list[dict[str, str | int]]]] = ticker.news
        articles = []
        for article in news_data_list:
            if not isinstance(article, dict):
                continue

            article['thumbnail'] = article.get('thumbnail', {}).get('resolutions', []) \
                if 'thumbnail' in article and isinstance(article['thumbnail'], dict) else []
            _article = NewsArticle(**article)

            title, summary, body, images = await parse_article(article=_article)
            _article.summary = summary
            _article.body = body
            articles.append(_article)
        news.append({ticker: articles})

    return news


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
    headers = await switch_headers()
    if not isinstance(article, RssArticle):
        return None, None, []
    # TODO learn how to use proxy on the downloader
    html = await download_article(link=article.link, headers=headers, timeout=60)
    if html is None:
        return None, None, []
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


async def find_related_tickers(article: RssArticle) -> list[str]:
    """
        **find_related_tickers**
            from the body of the article try learning what tickers could be related to the article
    :param article:
    :return:
    """

    return []
