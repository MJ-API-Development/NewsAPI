import asyncio
import random

import aiohttp

from src.exceptions import RequestError
from src.config import config_instance
from src.telemetry import capture_telemetry
from src.utils import user_agents


async def switch_headers() -> dict[str, str]:
    """
        this method is used to select a random header to use in parsing news
    :return:
    """
    user_agent = random.choice(user_agents)
    selected_header = {'User-Agent': user_agent}
    selected_header.update(
        {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*'})
    return selected_header

cloudflare_settings = config_instance().CLOUDFLARE_SETTINGS


class CloudflareProxy:
    """
    **CloudflareProxy**
        used to make requests with cloudflare api
            - this Uses CloudFlare Edge as Forward Proxy Servers
        tracks if there are too many errors and stops making requests through cloudflare
    """

    def __init__(self):
        self.worker_url: str = "https://proxy.eod-stock-api.site"
        self.api_endpoint: str = "https://api.cloudflare.com/client/v4"
        self.api_key = cloudflare_settings.CLOUD_FLARE_API_KEY
        self.api_email = cloudflare_settings.CLOUD_FLARE_EMAIL
        self.zone_id = cloudflare_settings.CLOUDFLARE_ZONE_ID
        self.worker_name = cloudflare_settings.CLOUDFLARE_WORKER_NAME

        self.error_count = 0
        self.error_thresh_hold = 60

    async def create_request_endpoint(self) -> str:
        return f"{self.api_endpoint}/zones/{self.zone_id}/workers/scripts/{self.worker_name}/fetch"

    # @capture_telemetry(name='make_request_with_cloudflare')
    async def make_request_with_cloudflare(self, url: str, method: str):
        """
            **make_request_with_cloudflare**
                will redirect requests through the cloudflare network
        :param url:
        :param method:
        :return:
        """
        try:
            headers: dict[str, str] = await switch_headers()
            headers.update({'X-SECURITY-TOKEN': config_instance().CLOUDFLARE_SETTINGS.SECURITY_TOKEN})
            if self.error_count < self.error_thresh_hold:
                request_url = f"{self.worker_url}?url={url}&method={method}"
            else:
                request_url = url

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url=request_url, timeout=96) as response:
                    # print(response)
                    response.raise_for_status()
                    if response.headers.get('Content-Type') == 'application/json':
                        data = await response.json()
                        print(data)
                        return data
                    return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            self.error_count += 1
            return None
        except Exception as e:
            raise RequestError()


cloud_flare_proxy = CloudflareProxy()
