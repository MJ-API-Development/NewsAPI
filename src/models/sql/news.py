from datetime import datetime, time

from dateutil.parser import parse, ParserError
from sqlalchemy import Column, String, Integer, inspect, ForeignKey, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.exc import DataError, OperationalError, IntegrityError, PendingRollbackError
from sqlalchemy import select
from sqlalchemy.orm import relationship, joinedload
from sqlalchemy.orm.exc import DetachedInstanceError

from src.connector.data_instance import Base, sessionType, mysql_instance
from src.exceptions import InputError
from src.utils import create_id


# from src.databases.models.ndb_datastore.news import RelatedTickers, Thumbnails


class NewsSentiment(Base):
    """
        stock_codes: a comma delimited list of stock codes related to the article
        article_uuid: used to retrieve the article from the datastore
        article_title: the actual title of the article
        sentiment_title: Sentiment analysis of the title
        sentiment_article: sentiment analysis of the actual article
        link: the actual url of the article in question
    """
    __tablename__ = 'news_sentiment'
    article_uuid: str = Column(String(64), ForeignKey('news.uuid'), index=True, primary_key=True)
    stock_codes: str = Column(String(255))
    title: str = Column(String(255))
    sentiment_title: str = Column(String(255), default=None)  # sentiment analysis for just the article Title
    article: str = Column(LONGTEXT, default=None)
    article_tldr: str = Column(String(255), default=None)
    sentiment_article: str = Column(String(255), default=None)  # sentiment analysis for the actual article
    link: str = Column(String(255))

    def __init__(self, article_uuid, stock_codes, title, link, sentiment_title=None, article=None, article_tldr=None,
                 sentiment_article=None):

        self.article_uuid = article_uuid
        self.stock_codes = stock_codes
        self.title = title
        self.sentiment_title = sentiment_title
        self.article = article
        self.article_tldr = article_tldr
        self.sentiment_article = sentiment_article
        self.link = link

    @classmethod
    def create_if_not_table(cls):
        if not inspect(mysql_instance.engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=mysql_instance.engine)

    def to_dict(self):
        return {
            'stock_codes': self.stock_codes,
            'title': self.title,
            'sentiment_title': self.sentiment_title,
            'article': self.article,
            'article_tldr': self.article_tldr,
            'sentiment_article': self.sentiment_article,
            'link': self.link,
        }  # return {c.key: getattr(self, c.key) for c in inspect(self).attrs.items()}

    def __str__(self) -> str:
        return f"<NewsSentiment=  Stock Code: {self.stock_codes}, Article: {self.article}, " \
               f"Title Sentiment: {self.sentiment_title}, Article Sentiment: {self.sentiment_article} >"

    def __bool__(self) -> bool:
        """
            return bool indicating if the model is valid
        :return:
        """
        return not not self.stock_codes

    @classmethod
    async def save_all(cls, instance_list, session: sessionType):
        """
        :param instance_list:
        :param session:
        :return:
        """
        # expensive but works
        # how the algorithm to create sentiment analyses works, in other words it will know
        # to skip news articles which are already done
        # article_uuid_set = {article.uuid for article in session.query(cls).all()}
        # new_instance_list = [instance for instance in instance_list if instance.uuid not in article_uuid_set]
        try:
            session.bulk_save_objects(instance_list)
            session.commit()
        except (DataError, OperationalError, IntegrityError, PendingRollbackError):
            # TODO need to log this error
            session.rollback()
            pass


# noinspection DuplicatedCode
def create_start_end_timestamps(_date: str) -> tuple[int, int]:
    try:
        date = parse(_date).date()
    except ParserError:
        raise InputError(description="Invalid date format, expected 'YYYY-MM-DD'")

    start_of_day = datetime.combine(date, time.min)
    end_of_day = datetime.combine(date, time.max)
    start_of_day = int(start_of_day.timestamp())
    end_of_day = int(end_of_day.timestamp())

    return end_of_day, start_of_day


# noinspection PyUnresolvedReferences
class _News:
    article_page_size = 10

    @classmethod
    async def get_by_uuid(cls, uuid: str, session: sessionType):
        return session.query(cls).filter(cls.uuid == uuid).first()

    @classmethod
    async def get_by_uuid_list(cls, uuid_list: list[str], session: sessionType):
        """returns all articles matching the supplied uuid lists"""
        return session.query(cls).filter(cls.uuid.in_(uuid_list)).all() if isinstance(uuid_list, list) else []

    @classmethod
    async def fetch_by_uuid(cls, uuid: str, session: sessionType):
        """returns only those entities that match the supplied uuid"""
        return session.query(cls).filter(cls.uuid == uuid).all()

    def __bool__(self) -> bool:
        ...

    @classmethod
    async def save_all(cls, instance_list: list, session: sessionType) -> None:
        """
            saves instances related to news articles
        :param instance_list:
        :param session:
        :return:
        """
        try:
            session.bulk_save_objects(instance_list, update_changed_only=True)
            session.commit()
        except (DataError, OperationalError, IntegrityError, PendingRollbackError):
            session.rollback()
            return

        return

    @classmethod
    def delete_by_uuid(cls, uuid: str, session: sessionType) -> bool:
        return bool(session.query(cls).filter(cls.uuid == uuid).delete())


class Thumbnails(Base, _News):
    """
        **Thumbnails**
    """
    __tablename__ = 'thumbnail'
    thumbnail_id = Column(String(16), primary_key=True)
    uuid: str = Column(String(255), ForeignKey("news.uuid", ondelete="CASCADE"), index=True)
    url: str = Column(String(255), index=True)
    width: int = Column(Integer)
    height: int = Column(Integer)
    tag: str = Column(String(255), index=True)

    def __init__(self, thumbnail_id: str, uuid: str, url: str, width: int, height: int, tag: str):
        self.thumbnail_id = thumbnail_id
        self.uuid = uuid
        self.url = url
        self.width = width
        self.height = height
        self.tag = tag

    def to_dict(self) -> dict:
        """
            returns a dictionary of the thumbnail
        """
        return {
            'thumbnail_id': self.thumbnail_id,
            'uuid': self.uuid,
            'url': self.url,
            'width': self.width,
            'height': self.height,
            'tag': self.tag}

    def __str__(self) -> str:
        """
        :return:
        """
        return f"<Thumbnail UUID: {self.uuid}, URL: {self.url}, width: {self.width}, height: {self.height}>"

    def __repr__(self) -> str:
        return f"<Thumbnail UUID: {self.uuid},  URL: {self.url}, width: {self.width}, height: {self.height}>"

    def __bool__(self) -> bool:
        return not not self.uuid


# noinspection DuplicatedCode
class RelatedTickers(Base, _News):
    """
    **RelatedTickers**
        Ticker Symbol related to the Current Financial News
    """
    __tablename__ = 'related_tickers'
    id: str = Column(String(255), primary_key=True)
    uuid: str = Column(String(255), ForeignKey("news.uuid", ondelete="CASCADE"), index=True)
    ticker: str = Column(String(16), index=True)
    stock_id: str = Column(String(16), index=True)

    def __init__(self, uuid: str, ticker: str, stock_id: str = None):
        self.id = create_id()
        self.uuid = uuid
        self.ticker = ticker
        self.stock_id = create_id()

    def to_dict(self) -> dict:
        """
        """
        return {
            'id': self.id,
            'uuid': self.uuid,
            'ticker': self.ticker,
            'stock_id': self.stock_id}

    def __str__(self) -> str:
        """
        :return:
        """
        return f"<RelatedTickers ticker: {self.ticker}>"

    def __repr__(self) -> str:
        return f"<RelatedTickers ticker: {self.ticker}>"

    def __bool__(self) -> bool:
        return not not self.uuid

    @classmethod
    async def fetch_by_ticker(cls, ticker: str, session: sessionType):
        latest_publish_time = session.query(func.max(News.providerPublishTime)).scalar()
        subquery = session.query(News.uuid).filter(News.providerPublishTime <= latest_publish_time).subquery()
        subquery_select = select(subquery.c.uuid)

        return session.query(cls).filter(cls.ticker == ticker, cls.uuid.in_(subquery_select)).join(News).order_by(
            -News.providerPublishTime).limit(cls.article_page_size).all()


# noinspection DuplicatedCode
class News(Base, _News):
    """
        **News**
            News
    """
    __tablename__ = 'news'
    uuid: str = Column(String(255), primary_key=True)
    title: str = Column(String(255), index=True)
    publisher: str = Column(String(126), index=True)
    link: str = Column(String(255))
    providerPublishTime: int = Column(Integer)
    created_at: int = Column(Integer)
    type: str = Column(String(32), index=True)
    sentiment: NewsSentiment = relationship('NewsSentiment', uselist=False, foreign_keys=[NewsSentiment.article_uuid],
                                            backref='news')
    tickers: list[RelatedTickers] = relationship('RelatedTickers', uselist=True, foreign_keys=[RelatedTickers.uuid],
                                                 backref='news')
    thumbnails: list[Thumbnails] = relationship('Thumbnails', uselist=True, foreign_keys=[Thumbnails.uuid],
                                                backref='news')

    # noinspection PyPep8Naming
    def __init__(self, uuid: str, title: str, publisher: str, link: str, providerPublishTime: int, _type: str):
        """
            **__init__**

        :param uuid:
        :param title:
        :param publisher:
        :param link:
        :param providerPublishTime:
        :param _type:
        """
        self.uuid = uuid
        self.title = title
        self.publisher = publisher
        self.created_at = int(datetime.now().timestamp())
        self.link = link
        self.providerPublishTime = providerPublishTime
        self.type = _type

    @property
    def datetime_published(self):
        return datetime.fromtimestamp(self.providerPublishTime)

    def to_dict(self) -> dict:
        article_dict = {
            'uuid': self.uuid,
            'title': self.title,
            'publisher': self.publisher,
            'link': self.link,
            'providerPublishTime': self.providerPublishTime,
            'created_at': self.created_at,
            'datetime_published': self.datetime_published,
            'type': self.type
        }

        try:
            if self.sentiment is not None:
                article_dict.update({'sentiment': self.sentiment.to_dict()})
        except DetachedInstanceError:
            pass

        try:
            if self.tickers is not None:
                article_dict.update({'tickers': [ticker.ticker for ticker in self.tickers]})
        except DetachedInstanceError:
            pass

        try:
            if self.thumbnails is not None:
                article_dict.update({'thumbnail': dict(resolutions=[thumb.to_dict() for thumb in self.thumbnails])})
        except DetachedInstanceError:
            pass

        return article_dict

    def __bool__(self) -> bool:
        return bool(self.uuid)

    @classmethod
    def create_if_not_table(cls):
        if not inspect(mysql_instance.engine).has_table(cls.__tablename__):
            Base.metadata.create_all(bind=mysql_instance.engine)

    def __str__(self) -> str:
        """
        :return:
        """
        return f"<News title: {self.title}, publisher: {self.publisher}, link: {self.link}, " \
               f"time: {self.providerPublishTime}, type: {self.type}"

    def __repr__(self) -> str:
        return f"<News title: {self.title}, publisher: {self.publisher}, link: {self.link}, " \
               f"time: {self.providerPublishTime}, type: {self.type}"

    @classmethod
    async def get_by_uuid_list(cls, uuid_list: list[str], session: sessionType):
        """Returns all articles matching the supplied uuid list, including sentiment relationship"""
        return session.query(cls).options(joinedload(cls.sentiment)).options(joinedload(cls.tickers)).options(
            joinedload(cls.thumbnails)).filter(cls.uuid.in_(uuid_list)).all() if isinstance(uuid_list, list) else []

    @classmethod
    async def fetch_by_day_published(cls, date_published: str, session: sessionType):
        """
            **fetch_by_day_published**
                Fetch by day published -- returns a list of News
            :param session:
            :param date_published:
            :return:
        """
        end_of_day, start_of_day = create_start_end_timestamps(_date=date_published)
        query = session.query(cls).options(joinedload(cls.sentiment), joinedload(cls.tickers),
                                           joinedload(cls.thumbnails))
        query = query.filter(cls.providerPublishTime >= start_of_day, cls.providerPublishTime <= end_of_day).limit(
            cls.article_page_size)
        return query.all()

    @classmethod
    async def fetch_by_publisher(cls, publisher: str, session: sessionType):
        """
        fetch by publisher -- returns a publisher , session.
        :param publisher:
        :param session:
        :return: list[Self]
        """
        return (
            session.query(cls)
            .options(joinedload(cls.sentiment))
            .options(joinedload(cls.tickers))
            .options(joinedload(cls.thumbnails))
            .order_by(-cls.providerPublishTime)
            .filter(cls.publisher == publisher)
            .limit(cls.article_page_size)
            .all()
        )

    @classmethod
    async def get_bounded(cls, upper_bound: int, session: sessionType):
        """
        **get_bounded**
            sorted by most recent - will return News Tickers Sentiment and Thumbnails
        :param session:
        :param upper_bound:
        :return:
        """
        return (
            session.query(cls)
            .order_by(-cls.providerPublishTime)
            .options(joinedload(cls.sentiment))
            .options(joinedload(cls.tickers))
            .options(joinedload(cls.thumbnails))
            .limit(upper_bound)
            .all()
        )

    @classmethod
    async def get_present_uuid_list(cls, session: sessionType) -> list[str]:
        """
            will obtain a list of uuid's for news articles which are already created
        """
        return session.query(cls.uuid).all()
        # return [news.uuid for news in news_list]

    @classmethod
    async def get_uuids_without_sentiment_analysis(cls, session: sessionType):
        """
            lookup all tables without sentiment analysis
        :param session:
        :return:
        """
        # Use a subquery to retrieve the UUIDs of all News objects with a corresponding NewsSentiment object
        subquery = select(cls.uuid).join(cls.sentiment)
        # Use the subquery to retrieve the UUIDs of all News objects without a corresponding NewsSentiment object
        query = select(cls).where(~cls.uuid.in_(subquery))
        # Execute the query and return the results as a list of News objects
        return session.execute(query).scalars().all()
