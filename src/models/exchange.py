
from pydantic import BaseModel


class Exchange(BaseModel):
    """
        Exchange Model must be the same as the model in the Database
        See StockAPI Exchange Model 
    """
    exchange_id: str
    name: str
    code: str
    operating_mic: str
    country: str
    currency_symbol: str

    class Config:
        title = "StockAPI Exchange Model"
