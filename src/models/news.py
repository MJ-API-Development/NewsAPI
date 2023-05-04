from datetime import datetime
import uuid as _uuid
from pydantic import BaseModel, validator, Field


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
    thumbnail: list[dict[str, str | int]] | None
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

