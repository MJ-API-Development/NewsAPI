import asyncio
import itertools
import json

from bs4 import BeautifulSoup
from pydantic import ValidationError

from src.parsers.motley_fool import parse_motley_article
from src.connector.data_connector import data_sink
from src.exceptions import ErrorParsingHTMLDocument
from src.models import RssArticle, NewsArticle
from src.tasks import download_article
from src.tasks.rss_feeds import parse_feeds
from src.tasks.utils import switch_headers, cloud_flare_proxy
from src.telemetry import capture_telemetry
from src.utils.my_logger import init_logger

news_scrapper_logger = init_logger('news-scrapper-logger')


async def scrape_news_yahoo(tickers: list[str], _chunk_size: int = 10) -> list[NewsArticle | RssArticle]:
    try:
        articles_tickers = []
        chunk_size = _chunk_size if len(tickers) > _chunk_size else len(tickers)

        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i + chunk_size]
            tasks = [ticker_articles(ticker=ticker) for ticker in chunk]
            results = await asyncio.gather(*tasks)
            articles_tickers.extend([articles for articles in results if isinstance(articles, list)])

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

        # article['thumbnail'] = get_thumbnail_resolutions(article=article)
        article.update({'thumbnail': get_thumbnail_resolutions(article=article)})
        # noinspection PyBroadException
        # news_scrapper_logger.info(f"Thumbnails : {article['thumbnail']}")
        try:
            # NOTE: sometimes there is a strange list error here, don't know why honestly

            _article: NewsArticle | None = NewsArticle(**article)
            news_scrapper_logger.info(f"Original Article Scrapped : {_article}")
            # news_scrapper_logger.info(f"Thumbnails : {_article.thumbnail}")
        except ValidationError as e:
            news_scrapper_logger.info(f'Error Creating NewsArticle: {str(e)}')
            _article = None

        article_not_saved = await data_sink.article_not_saved(article=article)
        if _article and article_not_saved:
            try:
                title, summary, body = await parse_article(article=_article)
                # Note: funny way of catching parser errors but hey - beggars cant be choosers
                _substring = "not supported on your current browser version"
                if summary and (_substring not in summary.casefold()):
                    _article.summary = summary
                if body and (_substring not in body.casefold()):
                    _article.body = body

                articles.append(_article)
                news_scrapper_logger.info(f"Added Article: {_article}")
            except Exception as e:
                news_scrapper_logger.info(f'error parsing article: {str(e)}')

    return articles


def get_thumbnail_resolutions(article: dict[str, dict[str, str | int] | list]) -> list[dict[str, str | int]]:
    """Gets the thumbnail resolutions for an article.
  Args:
    article: The article to get the thumbnail resolutions for.
  Returns:
    A list of thumbnail resolutions.
  """
    thumbnail: dict[str, str | int] = article.get('thumbnail')
    if thumbnail is None:
        return []
    return thumbnail.get('resolutions', [])


# noinspection PyUnusedLocal
@capture_telemetry(name='alternate_news_sources')
async def alternate_news_sources(*args, **kwargs) -> list[NewsArticle | RssArticle]:
    """
        **alternate_news_sources**
            search for news from alternate sources
    :return:
    """
    articles_list: list[NewsArticle | RssArticle] = await parse_feeds()
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


async def parse_article(article: NewsArticle | None) -> tuple[str | None, str | None, str | None]:
    """**parse_article**
    will parse articles from yfinance
    """
    if not article:
        return None, None, None

    _headers = await switch_headers()

    _html = await cloud_flare_proxy.make_request_with_cloudflare(url=article.link, method="GET")

    html = _html if _html is not None else await download_article(link=article.link, timeout=9600, headers=_headers)

    if html is None:
        return None, None, None
    try:
        soup = BeautifulSoup(html, 'html.parser')
        title: str = soup.find('h1').get_text() or soup.find('h2').get_text()
        summary: str = soup.find('p').get_text()
        body: str | None = None

        # Check if there is a "Read More" button
        read_more_button = soup.find('div', attrs={'class': 'caas-readmore'})

        if read_more_button is not None:
            try:
                read_more_url = read_more_button.find('a')['href']

                full_article_html = await download_article(link=read_more_url, timeout=9600, headers=_headers)

                if 'https://www.fool.com/' in read_more_url.casefold():
                    parsed_data = parse_motley_article(html=full_article_html)
                else:
                    parsed_data = {}

                if parsed_data:
                    body = parsed_data.get('content')

            except TypeError as e:
                news_scrapper_logger.error(f'Error parsing Article : {str(e)}')
                pass

        else:
            pass

        if body is None:
            try:
                body = ""
                for elem in soup.find_all('p'):
                    text = elem.get_text()
                    if text:
                        body += text

            except Exception as e:
                news_scrapper_logger.error(f'Error parsing Article : {str(e)}')
                pass

        return title, summary, body

    except Exception as e:
        news_scrapper_logger.error(f'Error parsing Article : {str(e)}')
        return None, None, None


# noinspection PyUnusedLocal
async def find_related_tickers(article: RssArticle) -> list[str]:
    """
        **find_related_tickers**
            from the body of the article try learning what tickers could be related to the article
    :param article:
    :return:
    """
    return []
