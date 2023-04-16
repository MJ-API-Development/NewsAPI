import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from models import RssArticle
from rss_feeds import parse_feeds
from src.tasks import download_article
from datetime import timedelta

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


async def scrape_news_yahoo(tickers: list[str]) -> list[dict[str, list[dict[str, str]]]]:
    """
    **scrape_news_yahoo**
    Scrapes financial articles from Yahoo Finance.

    :param tickers: A list of stock tickers to scrape news articles for.
    :return: A list of dictionaries containing ticker symbols as keys and a list of articles as values.
    """
    news = []
    request_session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'})
    for ticker in tickers:
        ticker = yf.Ticker(ticker=ticker.upper(), session=request_session)
        news_df = pd.DataFrame(ticker.news)
        articles = []
        for i in range(len(news_df)):
            article = news_df.iloc[i]
            articles.append(dict(
                uuid=article.get('uuid'),
                title=article.get('title'),
                publisher=article.get('publisher'),
                link=article.get('link'),
                providerPublishTime=article.get('providerPublishTime'),
                type=article.get('type'),
                thumbnail=article.get('thumbnail'),
                relatedTickers=article.get('relatedTickers')
            ))

        news.append({ticker: articles})

    return news


async def alternate_news_sources() -> list[dict[str, list[dict[str, str]]]]:
    """
        **alternate_news_sources**
            search for news from alternate sources
    :return:
    """
    articles_list: list[RssArticle] = await parse_feeds()
    for i, article in enumerate(articles_list):

        summary, body, images = await parse_article(article)
        # NOTE - probably nothing to lose sleep over, but if an article does not
        # have images it won't be saved
        if not all([summary, body, images]):
            continue

        article.body = body
        article.summary = summary
        article.thumbnail = images

        articles_list[i] = article

    return articles_list


async def parse_article(article: RssArticle) -> tuple[str, str, list[dict[str, str | int]]]:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    html = await download_article(link=article.link, headers=headers, timeout=60)
    if html is None:
        return None, None, None

    soup = BeautifulSoup(html, 'html.parser')
    summary = soup.find('p').get_text()
    body = ''
    images = []
    for elem in soup.select('div.article-content > *'):
        if elem.name == 'p':
            body += elem.get_text()
        elif elem.name == 'img':
            images.append(dict(src=elem['src'], alt=elem['alt'], width=elem['width'], height=elem['height']))
    return summary, body, images
