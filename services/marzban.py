import httpx
from loguru import logger
from bot.config import config
from datetime import datetime

class MarzbanAPI:
    def __init__(self):
        self.base_url = config.MARZBAN_URL.rstrip('/')
        self.username = config.MARZBAN_USERNAME
        self.password = config.MARZBAN_PASSWORD
        self.token = None

    async def _get_token(self):
        """Получение JWT токена для API Marzban."""
        async with httpx.AsyncClient() as client:
            try:
                data = {"username": self.username, "password": self.password}
                response = await client.post(f"{self.base_url}/api/admin/token", data=data)
                response.raise_for_status()
                self.token = response.json().get("access_token")
            except Exception as e:
                logger.error(f"Ошибка авторизации в Marzban: {e}")

    async def _request(self, method: str, endpoint: str, **kwargs):
        """Универсальный метод для запросов к API."""
        if not self.token:
            await self._get_token()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, f"{self.base_url}{endpoint}", headers=headers, **kwargs)
                if response.status_code == 401: # Token expired
                    await self._get_token()
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await client.request(method, f"{self.base_url}{endpoint}", headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Ошибка запроса к Marzban API ({endpoint}): {e}")
                return None

    async def create_user(self, username: str, expire_date: int, data_limit: int = 0):
        """Создание пользователя в Marzban с нужными inbound'ами."""
        # Настраиваем прокси под наше ядро
        proxies = {
            "vless": {},
            "shadowsocks": {}
        }
        # Указываем ТОЧНЫЕ названия inbounds из Xray конфигурации
        inbounds = {
            "vless": ["VLESS REALITY", "VLESS XHTTP"],
            "shadowsocks": ["Shadowsocks TCP"]
        }
        
        payload = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds,
            "expire": expire_date,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": "Created via Telegram Bot"
        }
        
        # Убрали on_hold параметры, так как они могут вызывать конфликты, если не поддерживаются версией
        result = await self._request("POST", "/api/user", json=payload)
        return result

    async def get_system_stats(self):
        """Получение статистики сервера (онлайн)."""
        return await self._request("GET", "/api/system")

    async def suspend_user(self, username: str):
        """Блокировка пользователя (например, за превышение лимита устройств)."""
        payload = {"status": "disabled"}
        return await self._request("PUT", f"/api/user/{username}", json=payload)

marzban_api = MarzbanAPI()
