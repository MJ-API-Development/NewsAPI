import pprint

import pandas as pd
import requests
import yfinance as yf

from src.models import NewsArticle


async def scrape_news_yahoo(tickers: list[str]) -> list[dict[str, list[dict[str, str]]]]:
    """
    **scrape_news_yahoo**
    Scrapes financial articles from Yahoo Finance.

    :param tickers: A list of stock tickers to scrape news articles for.
    :return: A list of dictionaries containing ticker symbols as keys and a list of articles as values.
    """
    news = []

    for ticker in tickers:
        ticker = yf.Ticker(ticker)
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


def alternate_news_sources(tickers: list[str]) -> list[dict[str, list[dict[str, str]]]]:
    """
        **alternate_news_sources**
            search for news from alternate sources
    :param tickers:
    :return:
    """
    news = []

    for ticker in tickers:
        ticker = yf.Ticker(ticker)
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


async def get_news(tickers: list[str]) -> list[NewsArticle]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    news = []
    for ticker in tickers:

        url = f"https://finance.yahoo.com/_finance_doubledown/api/resource/searchassist;searchTerm={ticker}"
        with requests.Session() as session:
            response = session.get(url=url, headers=headers)
            if response.status_code != 200:
                pprint.pprint(response.text)
                json_data = response.json()
                for article in json_data['stream']['items']:
                    news_article = NewsArticle(**article)
                    news.append(news_article)
                    pprint.pprint(news_article)

    return news

