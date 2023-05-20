import uuid as _uuid
from datetime import datetime

from pydantic import BaseModel, Field


# noinspection PyMethodParameters
class NewsArticle(BaseModel):
    """
    **NewsArticle**
        Used to parse YFinance Articles
    """
    uuid: _uuid.UUID = Field(default_factory=lambda: _uuid.uuid4())
    title: str
    publisher: str | None
    link: str
    providerPublishTime: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    type: str = Field(default='Story')
    thumbnail: list[dict[str, str | int]] | None = Field(default_factory=list())
    relatedTickers: list[str] = Field(default_factory=list())

    summary: str | None
    body: str | None

    @property
    def publish_time(self) -> datetime:
        """
            **publish_time**
                publish_time time the article was published
        :return:
        """
        return datetime.fromtimestamp(self.providerPublishTime)

    class Config:
        title = "YFinance Article Model"

