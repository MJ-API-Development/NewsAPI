
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from src.config import config_instance
from src.utils import camel_to_snake
from src.utils.my_logger import init_logger

Base = declarative_base()
sessionType = Session


class MYSQLDatabase:
    """Base class for database connection.
    """

    def __init__(self, database_url: str | None = None):
        self.settings = config_instance().DATABASE_SETTINGS
        self._logger = init_logger(camel_to_snake(self.__class__.__name__))
        try:
            db_url = database_url or self.settings.SQL_DB_URL
            self.engine = create_engine(url=db_url)
            self.get_session: sessionmaker = self.create_session(self.engine)
            config_instance().DEBUG and self._logger.info(f"Connected to database : {db_url}")
        except OperationalError:
            config_instance().DEBUG and self._logger.error("Unable to connect to MYSQL Database")

    def session_generator(self) -> Session:
        while True:
            for _session in [self.create_session(self.engine) for _ in range(self.settings.TOTAL_CONNECTIONS)]:
                yield _session

    # noinspection PyUnusedLocal
    def create_session(self, engine) -> sessionmaker:
        return sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @classmethod
    def create_engine(cls, db_url: str):
        """
        :param db_url:
        :return:
        """
        return create_engine(db_url)

    def save_all(self, instance_list: list):
        with self.get_session as session:
            for instance in instance_list:
                session.add(instance)
            session.commit()

    def create_all_tables(self):
        Base.metadata.create_all(bind=self.engine)


mysql_instance = MYSQLDatabase()
