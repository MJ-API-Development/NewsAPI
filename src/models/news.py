from datetime import datetime
import uuid
from pydantic import BaseModel, validator, Field


# noinspection PyMethodParameters
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

    @validator('link')
    def check_link(cls, v):
        """
        **check_link**
            ensure that the link is a valid url
        :param v:
        :return:
        """
        if not v.startswith('https'):
            raise ValueError('Link must start with https')
        return v

    @validator('uuid')
    def check_uuid(cls, v):
        """
        **check_uuid**
            ensure that the uuid is a valid uuid
        :param v:
        :return:
        """
        if not isinstance(v, uuid.UUID):
            raise ValueError('UUID must be a valid UUID')
        return v
