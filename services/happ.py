import urllib.parse
import aiohttp
from loguru import logger
from bot.config import config

class HappService:
    def __init__(self, provider_code: str, auth_key: str):
        self.provider_code = provider_code
        self.auth_key = auth_key
        self.install_api = "https://api.happ-proxy.com/api/add-install"
        self.crypto_api = "https://crypto.happ.su/api-v2.php"

    async def _get_install_id(self, limit: int) -> str | None:
        params = {
            "provider_code": self.provider_code,
            "auth_key": self.auth_key,
            "install_limit": limit
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.install_api, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("rc") == 1:
                            install_code = data.get("install_code")
                            logger.info(f"✅ Получен лимит устройств: {limit}, код: {install_code}")
                            return install_code
                        else:
                            logger.error(f"❌ Ошибка API HAPP-Proxy: {data.get('msg')}")
                            return None
                    else:
                        logger.error(f"❌ HTTP Ошибка {response.status} при запросе к HAPP-Proxy")
                        return None
            except Exception as e:
                logger.error(f"❌ Ошибка сети при запросе к HAPP-Proxy: {e}")
                return None

    async def encrypt_link(self, raw_url: str, title: str = "💎 Premium Connect", limit: int = 3) -> str:
        """
        Собирает идеальную ссылку: подписка + название с эмодзи + HWID лимит + DPI обход -> crypt5
        """
        try:
            if not self.provider_code or not self.auth_key:
                logger.warning("HAPP API keys not configured. Returning raw URL.")
                return raw_url

            install_id = await self._get_install_id(limit)
            if not install_id:
                return raw_url
            
            # 1. Формируем технические параметры (DPI и HWID)
            params = {
                "installid": install_id,
                "fragment": "1-10,5-20,tlshello" # Обход DPI
            }
            query_string = urllib.parse.urlencode(params)
            
            # 2. Добавляем эстетику (Название и иконки)
            # Кодируем название (urlencode), чтобы пробелы и эмодзи корректно передались по HTTP
            safe_title = urllib.parse.quote(title)
            
            # 3. Собираем "Франкенштейна" строго по документации HAPP
            # Формат: URL#Title?Params
            complex_url = f"{raw_url}#{safe_title}?{query_string}"
            logger.info(f"🔗 Подготовлена ссылка для шифрования: {complex_url}")
            
            # 4. Отправляем в крипто-кузницу (HAPP API v2)
            headers = {"Content-Type": "application/json"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.crypto_api, 
                    json={"url": complex_url}, 
                    headers=headers, 
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        encrypted_link = data.get("encrypted_link")
                        
                        if encrypted_link:
                            logger.info("✅ Ссылка успешно зашифрована в crypt5!")
                            return encrypted_link
                        else:
                            logger.error(f"❌ Ключ 'encrypted_link' не найден: {data}")
                            return raw_url
                    else:
                        logger.error(f"❌ Ошибка API HAPP: {response.status} - {await response.text()}")
                        return raw_url
        except Exception as e:
            logger.error(f"❌ Сетевая ошибка при шифровании HAPP: {e}")
            return raw_url # В случае ошибки отдаем сырую ссылку

    async def shorten_url(self, url: str) -> str:
        """Сокращает ссылку через локальный Redis (aiohttp)."""
        try:
            from bot.main import generate_short_link
            return await generate_short_link(url)
        except Exception as e:
            logger.error(f"URL Shortening error: {e}")
        return url

# Инициализируем синглтон
happ_service = HappService(provider_code=config.HAPP_PROVIDER_CODE, auth_key=config.HAPP_AUTH_KEY)
