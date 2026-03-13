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
        async with httpx.AsyncClient(timeout=5.0) as client:
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
            
            # Приклеиваем параметры для обхода DPI (фрагментация)
            params = {
                "fragment": "1-10,5-20,tlshello",
                "installid": install_id
            }
            
            # Проверяем, есть ли уже параметры в ссылке
            separator = "&" if "?" in raw_url else "?"
            query_string = urllib.parse.urlencode(params)
            
            # Готовая длинная ссылка со всеми правилами
            complex_url = f"{raw_url}{separator}{query_string}"
            
            safe_title = urllib.parse.quote(title)
            assembled_url = f"{complex_url}#{safe_title}"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.crypto_api, json={"url": assembled_url})
                if response.status_code == 200:
                    encrypted_link = response.text.strip().strip('"')
                    return encrypted_link
                raise ConnectionError(f"Failed to encrypt URL. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"HAPP Encryption error: {e}")
            return raw_url # В случае ошибки отдаем сырую ссылку

    async def shorten_url(self, url: str) -> str:
        """Сокращает ссылку через локальный Redis (FastAPI)."""
        try:
            from web_app import generate_short_link
            return await generate_short_link(url)
        except Exception as e:
            logger.error(f"URL Shortening error: {e}")
        return url

# Инициализируем синглтон
happ_service = HappService(provider_code=config.HAPP_PROVIDER_CODE, auth_key=config.HAPP_AUTH_KEY)
