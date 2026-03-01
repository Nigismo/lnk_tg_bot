import asyncio
import re
from loguru import logger
from redis.asyncio import Redis
from bot.config import config
from services.marzban import marzban_api

# Регулярное выражение для парсинга access.log Xray/Marzban
LOG_PATTERN = re.compile(r"accepted\s+(?P<ip>\d+\.\d+\.\d+\.\d+):\d+\s+\[(?P<user>[^\]]+)\]")

class IPLimiter:
    def __init__(self):
        self.redis = Redis.from_url(config.redis_url, decode_responses=True)
        self.limit = 3 # Максимум 3 устройства (IP)
        self.window = 300 # 5 минут

    async def process_log_line(self, line: str):
        """Обработка одной строки лога."""
        match = LOG_PATTERN.search(line)
        if match:
            ip = match.group("ip")
            user = match.group("user")
            
            key = f"ips:{user}"
            # Добавляем IP в Redis Set
            await self.redis.sadd(key, ip)
            # Устанавливаем TTL, если его нет
            if await self.redis.ttl(key) == -1:
                await self.redis.expire(key, self.window)
            
            # Проверяем количество уникальных IP
            ip_count = await self.redis.scard(key)
            if ip_count > self.limit:
                logger.warning(f"Пользователь {user} превысил лимит устройств ({ip_count}/{self.limit}). Блокировка.")
                await marzban_api.suspend_user(user)
                # Здесь можно добавить отправку уведомления пользователю через бота
                # await bot.send_message(user_id, "Ваш аккаунт заблокирован за использование более 3 устройств.")

    async def tail_logs(self):
        """Чтение логов Marzban в реальном времени."""
        log_file = "/marzban_data/access.log"
        try:
            # Используем aiofiles или subprocess для tail -F
            process = await asyncio.create_subprocess_exec(
                "tail", "-F", log_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("Запущен мониторинг access.log для анти-шейр системы.")
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                await self.process_log_line(line.decode("utf-8").strip())
        except Exception as e:
            logger.error(f"Ошибка чтения логов: {e}")

ip_limiter = IPLimiter()
