
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

    @property
    def publish_time(self) -> datetime:
        return datetime.fromtimestamp(self.providerPublishTime)

    class Config:
        title = "YFinance Article Model"

    @validator('link')
    def check_link(cls, v):
        """
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
            ensure that the uuid is a valid uuid
        :param v:
        :return:
        """
        if not isinstance(v, uuid.UUID):
            raise ValueError('UUID must be a valid UUID')
        return v

