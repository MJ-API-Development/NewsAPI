from pydantic import BaseModel


class Stock(BaseModel):
    """
    **Stock**

        Stock Model , Same as the Stock Model in the database
        see StockAPI

    """
    exchange_id: str
    exchange_code: str
    stock_id: str
    code: str
    name: str
    country: str
    currency: str
    stock_type: str

    class Config:
        title = "Stock Model"
