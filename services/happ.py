import urllib.parse
import httpx
from loguru import logger
from bot.config import config

class HappService:
    def __init__(self, provider_code: str, auth_key: str):
        self.provider_code = provider_code
        self.auth_key = auth_key
        self.install_api = "https://api.happ-proxy.com/api/add-install"
        self.crypto_api = "https://crypto.happ.su/api-v2.php"

    async def _get_install_id(self, limit: int) -> str:
        params = {
            "provider_code": self.provider_code,
            "auth_key": self.auth_key,
            "install_limit": limit
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.install_api, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("rc") == 1:
                return data.get("install_code")
            raise ValueError(f"HAPP API Error: {data.get('msg')}")

    async def encrypt_link(self, raw_url: str, title: str, limit: int = 2) -> str:
        try:
            if not self.provider_code or not self.auth_key:
                logger.warning("HAPP API keys not configured. Returning raw URL.")
                return raw_url

            install_id = await self._get_install_id(limit)
            safe_title = urllib.parse.quote(title)
            assembled_url = f"{raw_url}#{safe_title}?installid={install_id}"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.crypto_api, json={"url": assembled_url})
                if response.status_code == 200:
                    return response.text.strip()
                raise ConnectionError(f"Failed to encrypt URL. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"HAPP Encryption error: {e}")
            return raw_url # В случае ошибки отдаем сырую ссылку

# Инициализируем синглтон
happ_service = HappService(provider_code=config.HAPP_PROVIDER_CODE, auth_key=config.HAPP_AUTH_KEY)
