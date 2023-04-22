"""
    will use this to create a connection between the cron server and this
    micro service
"""
from pydantic import BaseModel


class Channel(BaseModel):
    pass


class RedisMessageQueue:

    def __init__(self):
        pass

    async def create_channel(self, channel_name: str) -> bool:
        """
            **create_channel**
                creates a channel if one does not already exists
        :return:
        """
        pass

    async def join_channel(self, channel_name: str) -> Channel:
        """
            will join and listen to messages on channel
        :return:
        """
        pass

    async def send_message(self, message: str) -> bool:
        pass

    async def process_messages(self, channel: Channel):
        pass
