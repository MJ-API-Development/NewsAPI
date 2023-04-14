
from datetime import datetime
import uuid
from pydantic import BaseModel


class NewsArticle(BaseModel):
    """
    **NewsArticle**

        Used to parse YFinance Articles
    """
    uuid: uuid.UUID
    title: str
    publisher: str
    link: str
    providerPublishTime: int
    type: str
    thumbnail: str
    relatedTickers: list[str]

    @property
    def publish_time(self) -> datetime:
        return datetime.fromtimestamp(self.providerPublishTime)

    class Config:
        title = "YFinance Article Model"
