from pydantic import BaseModel, Field, validator
import uuid as _uuid
from datetime import datetime

from src.utils import create_id


# noinspection PyMethodParameters
class RssArticle(BaseModel):
    """
        **RssArticle**
            a model to parse an article feed
            feeds must be taken from google

    """
    uuid: _uuid.UUID = Field(default_factory=lambda: _uuid.uuid4())
    title: str
    link: str
    summary: str | None
    body: str | None
    thumbnail: list[dict[str, str | int]] | None
    published: str = Field(default=False)
    providerPublishTime: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    class Config:
        title = "Google RSS Article Model"

    @validator('published')
    def published_validator(cls, v):
        """

        :param v:
        :return:
        """
        return v if v else int(datetime.now().timestamp())

    @validator('link')
    def link_validator(cls, v):
        """
            ensure that the link is a valid url

        :param v:
        :return:
        """
        return v if v.startswith('https') else 'https://' + v
