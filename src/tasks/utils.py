import random
import asyncio
import aiohttp
import requests
from src.config import config_instance


async def switch_headers() -> dict[str, str]:
    """
        this method is used to select a random header to use in parsing news
    :return:
    """
    selected_header = random.choice([
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:55.0) Gecko/20100101 Firefox/55.0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/40.15063.0.0'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0'
        }
    ])
    selected_header.update(
        {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': '*/*'})
    return selected_header


class CloudflareProxy:
    """
        used to make requests with cloudflare api
    """

    def __init__(self):
        self.worker_url: str = "https://proxy.eod-stock-api.site"
        self.api_endpoint: str = "https://api.cloudflare.com/client/v4"
        self.api_key = config_instance().CLOUDFLARE_SETTINGS.CLOUD_FLARE_API_KEY
        self.api_email = config_instance().CLOUDFLARE_SETTINGS.CLOUD_FLARE_EMAIL
        self.zone_id = config_instance().CLOUDFLARE_SETTINGS.CLOUDFLARE_ZONE_ID
        self.worker_name = "proxytask"

    async def create_request_endpoint(self) -> str:
        return f"{self.api_endpoint}/zones/{self.zone_id}/workers/scripts/{self.worker_name}/fetch"

    async def _make_request_with_cloudflare(self, url: str, method: str):
        """

        :param url:
        :param method:
        :return:
        """
        api_endpoint: str = await self.create_request_endpoint()
        headers = {
            "X-Auth-Email": self.api_email,
            "X-Auth-Key": f"{self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "url": url,
            "method": method
        }
        print(f"Making request : {url}")
        response = requests.post(api_endpoint, headers=headers, json=data)
        print("RESPONSE ", response.text)

        return response

    async def make_request_with_cloudflare(self, url: str, method: str):
        try:
            headers = await switch_headers()
            request_url = f"{self.worker_url}?url={url}&method={method}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url=request_url, timeout=9600) as response:
                    response.raise_for_status()
                    text: str = await response.text()
                    return text
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None


cloud_flare_proxy = CloudflareProxy()
