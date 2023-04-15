from pydantic import BaseModel, Field
import uuid as _uuid
from datetime import datetime

from src.utils import create_id


class RssArticle(BaseModel):
    """
        **RssArticle**
            a model to parse an article feed
            feeds must be taken from google

    """
    uuid: _uuid.UUID = Field(default_factory=lambda: _uuid.UUID(bytes=create_id().encode('utf-8')))
    title: str
    link: str
    summary: str | None
    published: str = Field(default=False)
    providerPublishTime: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    class Config:
        title = "Google RSS Article Model"
