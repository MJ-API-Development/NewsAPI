import functools
import logging
import socket
import sys
from src.config import config_instance


class AppLogger:
    logging_file = f'logs/{config_instance().LOGGING.filename}'

    def __init__(self, name: str, is_file_logger: bool = False, log_level: int = logging.INFO):
        logger_name = name if name else config_instance().APP_SETTINGS.APP_NAME
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(level=log_level)

        handler = logging.FileHandler(self.logging_file) if is_file_logger else logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


@functools.lru_cache
def init_logger(name: str = "financial-news-parser"):
    """
        should include a future version which uses azure monitor to create log messages
    :param name:
    :return:
    """
    is_development = socket.gethostname().casefold() == config_instance().DEVELOPMENT_SERVER_NAME.casefold()
    logger = AppLogger(name=name, is_file_logger=not is_development, log_level=logging.INFO)
    return logger.logger
