from fastapi import APIRouter

articles_router = APIRouter()


@articles_router.api_route(path='/api/v2/financial-news/{ticker}', methods=['GET'], include_in_schema=True)
def financial_news_by_ticker(ticker: str):
    """

    :param ticker:
    :return:
    """
    pass

