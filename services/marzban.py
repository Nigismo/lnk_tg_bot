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
        self.token_expires_at = 0

    async def _get_token(self):
        """Получение JWT токена для API Marzban."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                data = {"username": self.username, "password": self.password}
                response = await client.post(f"{self.base_url}/api/admin/token", data=data)
                response.raise_for_status()
                token_data = response.json()
                self.token = token_data.get("access_token")
                # Marzban токен обычно живет долго, кэшируем на 1 час (3600 секунд)
                self.token_expires_at = datetime.utcnow().timestamp() + 3600
            except Exception as e:
                logger.error(f"Ошибка авторизации в Marzban: {e}")

    async def _request(self, method: str, endpoint: str, **kwargs):
        """Универсальный метод для запросов к API."""
        # Проверяем, есть ли токен и не истек ли он
        if not self.token or datetime.utcnow().timestamp() >= self.token_expires_at:
            await self._get_token()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.request(method, f"{self.base_url}{endpoint}", headers=headers, **kwargs)
                if response.status_code == 401: # Token expired
                    await self._get_token()
                    headers["Authorization"] = f"Bearer {self.token}"
                    response = await client.request(method, f"{self.base_url}{endpoint}", headers=headers, **kwargs)
                
                if response.status_code == 404:
                    return None
                
                if response.status_code >= 400:
                    logger.error(f"Marzban API Error ({response.status_code}): {response.text}")
                    
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.error(f"HTTP Error к Marzban API ({endpoint}): {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Ошибка запроса к Marzban API ({endpoint}): {e}")
                return None

    async def create_user(self, username: str, expire_date: int, data_limit: int = 0):
        """Создание пользователя в Marzban с лимитом устройств."""
        payload = {
            "username": username,
            "expire": expire_date,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": "Created via Telegram Bot",
            "on_hold_timeout": "2026-01-01T00:00:00",
            "on_hold_expire_duration": 0,
            # ДОБАВЛЯЕМ ЯВНОЕ УКАЗАНИЕ ПРОТОКОЛОВ (Защита от 500 ошибки)
            "proxies": {
                "vless": {
                    "flow": "xtls-rprx-vision"
                }
            }
        }
        
        result = await self._request("POST", "/api/user", json=payload)
        return result

    async def get_system_stats(self):
        """Получение статистики сервера (онлайн)."""
        return await self._request("GET", "/api/system")

    async def get_user(self, username: str):
        """Получение пользователя из Marzban."""
        return await self._request("GET", f"/api/user/{username}")

    async def suspend_user(self, username: str):
        """Блокировка пользователя (например, за превышение лимита устройств)."""
        payload = {"status": "disabled"}
        return await self._request("PUT", f"/api/user/{username}", json=payload)

    async def update_user(self, username: str, expire: int = None, status: str = None):
        """Обновление пользователя (продление подписки)."""
        payload = {}
        if expire is not None:
            payload["expire"] = expire
        if status is not None:
            payload["status"] = status
        return await self._request("PUT", f"/api/user/{username}", json=payload)

marzban_api = MarzbanAPI()
