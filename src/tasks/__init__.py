"""
Helper functions to obtain ticker symbols
    utils for searching through articles
"""
import asyncio
from datetime import datetime, timedelta, time

import aiohttp
import feedparser
import requests
from bs4 import BeautifulSoup
from requests_cache import CachedSession

from src.config import config_instance
from src.exceptions import RequestError
from src.models import Exchange, Stock, RssArticle
from src.tasks.utils import switch_headers
from src.telemetry import capture_telemetry
from src.utils.my_logger import init_logger

tasks_logger = init_logger('tasks-logger')

request_session = CachedSession('finance_news.cache', use_cache_dir=True,
                                cache_control=True,
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
                                stale_if_error=True  # In case of request errors, use stale cache data if possible
                                )


async def get_exchange_tickers(exchange_code: str) -> list[Stock]:
    """
    **get_exchange_tickers**
        obtains a list of stocks for a given exchange
    :param exchange_code:
    :return:
    """
    url: str = f'{config_instance().GATEWAY_API.EXCHANGE_STOCK_ENDPOINT}/{exchange_code}'
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
    url: str = f'{config_instance().GATEWAY_API.EXCHANGES_ENDPOINT}'
    params: dict = dict(api_key=config_instance.EOD_STOCK_API_KEY)

    response: requests.Response = request_session.get(url=url, params=params)
    response.raise_for_status()

    if response.headers.get('Content-Type') == 'application/json':
        response_data: dict[str, str | bool | dict[str, str]] = response.json()
        if response_data.get('status', False):
            exchange_list: list[dict[str, str]] = response_data.get('payload')

            return [Exchange(**exchange) for exchange in exchange_list]
    return []


@capture_telemetry(name='parse_google_feeds')
async def parse_google_feeds(rss_url: str) -> list[RssArticle]:
    """
        **parse_google_feeds**
            will parse google rss feeds for specific subject articles
<id>tag:google.com,2005:reader/user/00244493797674210195/state/com.google/alerts/1129709253388904655</id>
<title>Google Alert - Financial News</title>
<link href="https://www.google.com/alerts/feeds/XXX/XXX" rel="self"/>
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
        if entry is not None:
            article_entry = dict(title=entry.title, link=entry.link, published=entry.updated)
            articles_list.append(RssArticle(**article_entry))
    tasks_logger.info(f"total articles found : {len(articles_list)}")
    return articles_list


@capture_telemetry(name='do_soup')
async def do_soup(html) -> tuple[str, str]:
    """
        parse the whole document and return formatted text
    :param html:
    :return:
    """
    soup = BeautifulSoup(html, 'html.parser')
    paragraphs = soup.find_all('p')
    return paragraphs[0], '\n\n'.join([p.get_text() for p in paragraphs])


@capture_telemetry(name='download_article')
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
        raise RequestError()


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
    current_time: time = datetime.now().time()
    schedule_time: time = await convert_to_time(schedule_time)

    # Calculate the difference between the schedule time and current time in minutes
    time_diff: int = abs(schedule_time.hour - current_time.hour) * 60 + abs(schedule_time.minute - current_time.minute)
    tasks_logger.info(f"testing if we can run task : {time_diff}")
    # Check if the time difference is less than or equal to 10 minutes and the task has not already run
    return time_diff <= 15 and not task_details.task_ran


@capture_telemetry(name='get_meme_tickers')
async def get_meme_tickers(count: int = 150, offset: int = 0) -> dict[str, str]:
    """
    Returns a dictionary of ticker symbols and company names for Mexican stocks.
    :return: A dictionary of ticker symbols and company names for Mexican stocks.
    """
    url = f"{config_instance().MEME_TICKERS_URI}?count={count}&offset={offset}"
    headers = await switch_headers()
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

    tasks_logger.info(tickers)

    return tickers





async def get_meme_tickers_us() -> dict[str, str]:
    """
    :return:
    """
    return {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "AMZN": "Amazon.com, Inc.",
        "GOOGL": "Alphabet Inc.",
        "FB": "Meta Platforms, Inc.",
        "NVDA": "NVIDIA Corporation",
        "NFLX": "Netflix, Inc.",
        "TSLA": "Tesla, Inc.",
        "JPM": "JPMorgan Chase & Co.",
        "V": "Visa Inc.",
        "BAC": "Bank of America Corporation",
        "WMT": "Walmart Inc.",
        "JNJ": "Johnson & Johnson",
        "PG": "Procter & Gamble Co.",
        "KO": "The Coca-Cola Company",
        "PEP": "PepsiCo, Inc.",
        "CSCO": "Cisco Systems, Inc.",
        "INTC": "Intel Corporation",
        "ORCL": "Oracle Corporation",
        "AMD": "Advanced Micro Devices, Inc.",
        "PYPL": "PayPal Holdings, Inc.",
        "CRM": "Salesforce.com, Inc.",
        "ATVI": "Activision Blizzard, Inc.",
        "EA": "Electronic Arts Inc.",
        "TTD": "The Trade Desk, Inc.",
        "ZG": "Zillow Group, Inc.",
        "MTCH": "Match Group, Inc.",
        "YELP": "Yelp Inc.",
        "BABA": "Alibaba Group Holding Limited",
        "NKE": "Nike, Inc.",
        "DIS": "The Walt Disney Company",
        "IBM": "International Business Machines Corporation",
        "UNH": "UnitedHealth Group Incorporated",
        "HD": "The Home Depot, Inc.",
        "MMM": "3M Company",
        "GS": "The Goldman Sachs Group, Inc.",
        "AXP": "American Express Company",
        "VZ": "Verizon Communications Inc.",
        "C": "Citigroup Inc.",
        "GE": "General Electric Company",
        "PFE": "Pfizer Inc.",
        "WFC": "Wells Fargo & Company",
        "CVX": "Chevron Corporation",
        "XOM": "Exxon Mobil Corporation",
        "BP": "BP p.l.c.",
        "T": "AT&T Inc.",
        "GM": "General Motors Company",
        "F": "Ford Motor Company"
    }


async def get_meme_tickers_canada():
    """
    :return:
    """
    canadian_stocks = {
        'SHOP': 'Shopify Inc.',
        'BNS': 'Bank of Nova Scotia',
        'TD': 'Toronto-Dominion Bank',
        'RY': 'Royal Bank of Canada',
        'BMO': 'Bank of Montreal',
        'ENB': 'Enbridge Inc.',
        'TRP': 'TC Energy Corporation',
        'SU': 'Suncor Energy Inc.',
        'CNQ': 'Canadian Natural Resources Limited',
        'MFC': 'Manulife Financial Corporation',
        'RYAAY': 'Ryanair Holdings plc',
        'FTS': 'Fortis Inc.',
        'CP': 'Canadian Pacific Railway Limited',
        'POT': 'Potash Corporation of Saskatchewan Inc.',
        'CVE': 'Cenovus Energy Inc.',
        'BCE': 'BCE Inc.',
        'TRI': 'Thomson Reuters Corporation',
        'CNTR': 'Contrarian Metal Resources Inc.',
        'WEED': 'Canopy Growth Corporation',
        'MRU': 'Metro Inc.',
        'MG': 'Magna International Inc.',
        'QSR': 'Restaurant Brands International Inc.',
        'HSE': 'Husky Energy Inc.',
        'LNR': 'Lorne Resources Inc.',
        'EMA': 'Emera Incorporated',
        'VET': 'Vermilion Energy Inc.',
        'SLF': 'Sun Life Financial Inc.',
        'GIB.A': 'CGI Inc.',
        'CM': 'Canadian Imperial Bank of Commerce',
        'TECK.A': 'Teck Resources Limited',
        'SNC': 'SNC-Lavalin Group Inc.',
        'TRQ': 'Turquoise Hill Resources Ltd.',
        'IPL': 'Inter Pipeline Ltd.',
        'GIL': 'Gildan Activewear Inc.',
        'CNR': 'Canadian National Railway Company',
        'AEM': 'Agnico Eagle Mines Limited',
        'K': 'Kinross Gold Corporation',
        'EMA.A': 'Emera Incorporated',
        'FNV': 'Franco-Nevada Corporation',
        'YRI': 'Yamana Gold Inc.',
        'PXT': 'Parex Resources Inc.',
        'VII': 'Seven Generations Energy Ltd.',
        'AC': 'Air Canada',
        'IMO': 'Imperial Oil Limited',
        'WFT': 'West Fraser Timber Co. Ltd.',
        'CPG': 'Crescent Point Energy Corp.',
        'MEG': 'MEG Energy Corp.',
        'TOU': 'Tourmaline Oil Corp.',
    }

    return canadian_stocks


async def get_meme_tickers_brazil() -> dict[str, str]:
    """

    :return:
    """
    brazilian_stocks = {
        'ABEV3': 'Ambev S.A.',
        'BBAS3': 'Banco do Brasil S.A.',
        'BBDC3': 'Banco Bradesco S.A.',
        'BBDC4': 'Banco Bradesco S.A.',
        'BBSE3': 'BB Seguridade Participações S.A.',
        'BEEF3': 'Minerva S.A.',
        'BIDI11': 'Banco Inter S.A.',
        'BPAC11': 'BTG Pactual Group',
        'BRDT3': 'Petrobras Distribuidora S.A.',
        'BRFS3': 'BRF S.A.',
        'BRKM5': 'Braskem S.A.',
        'BRML3': 'BR Malls Participações S.A.',
        'BTOW3': 'B2W Digital Participações S.A.',
        'CCRO3': 'CCR S.A.',
        'CIEL3': 'Cielo S.A.',
        'CMIG4': 'CEMIG - Companhia Energética de Minas Gerais',
        'CPFE3': 'CPFL Energia S.A.',
        'CRFB3': 'Carrefour Brasil Comércio e Participações S.A.',
        'CSAN3': 'Cosan S.A.',
        'CSNA3': 'Companhia Siderúrgica Nacional',
        'CYRE3': 'Cyrela Brazil Realty S.A.',
        'ECOR3': 'Ecorodovias Infraestrutura e Logística S.A.',
        'EGIE3': 'Engie Brasil Energia S.A.',
        'ELET3': 'Centrais Elétricas Brasileiras S.A. - Eletrobras',
        'ELET6': 'Centrais Elétricas Brasileiras S.A. - Eletrobras',
        'EMBR3': 'Embraer S.A.',
        'ENBR3': 'EDP - Energias do Brasil S.A.',
        'ENEV3': 'Eneva S.A.',
        'EQTL3': 'Equatorial Energia S.A.',
        'EZTC3': 'EZTEC Empreendimentos e Participações S.A.',
        'FLRY3': 'Fleury S.A.',
        'GGBR4': 'Gerdau S.A.',
        'GNDI3': 'Grupo NotreDame Intermédica',
        'GOAU4': 'Metalúrgica Gerdau S.A.',
        'HAPV3': 'Hapvida Participações e Investimentos S.A.',
        'HGTX3': 'Cia. Hering S.A.',
        'HYPE3': 'Hypera S.A.',
        'ITSA4': 'Itaúsa - Investimentos Itaú S.A.',
        'ITUB4': 'Itaú Unibanco Holding S.A.',
        'JBSS3': 'JBS S.A.',
        'KLBN11': 'Klabin S.A.',
        'LAME4': 'Lojas Americanas S.A.',
        'LREN3': 'Lojas Renner S.A.',
        'MGLU3': 'Magazine Luiza S.A.',
        'MRFG3': 'Marfrig Global Foods S.A.',
        'MRVE3': 'MRV Engenharia e Participações S.A.',
        'MULT3': 'Multiplan Empreendimentos Imobiliários S.A.'
    }
    return brazilian_stocks
