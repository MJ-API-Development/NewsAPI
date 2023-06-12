from datetime import datetime
from pydantic import BaseModel, Field, validator


class Thumbnail(BaseModel):
    url: str
    width: int
    height: int
    tag: str


# noinspection PyMethodParameters
class NewsArticle(BaseModel):
    """
    **NewsArticle**
        Used to parse YFinance Articles
    """
    uuid: str
    title: str
    publisher: str | None
    link: str
    providerPublishTime: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    type: str = Field(default='Story')
    thumbnail: list[Thumbnail] | None
    relatedTickers: list[str] | None

    summary: str | None
    body: str | None

    def __bool__(self):
        return self.uuid is not None

    @validator('relatedTickers', pre=True)
    def validate_tickers(cls, value) -> list[str]:
        if isinstance(value, str):
            return [ticker.strip().upper() for ticker in value.split(",")]
        return value

    @validator('thumbnail', pre=True)
    def validate_thumbnail(cls, value):
        if isinstance(value, list):
            for thumb in value:
                if not isinstance(thumb, dict):
                    raise ValueError("Thumbnail must be a dictionary")
            return [Thumbnail(**thumb) for thumb in value]
        return value

    @validator('summary', pre=True)
    def validate_summary(cls, value):
        if value == "":
            return None
        return value

    @validator('body', pre=True)
    def validate_body(cls, value):
        if value == "":
            return None
        return value

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
        anystr_strip_whitespace = True
