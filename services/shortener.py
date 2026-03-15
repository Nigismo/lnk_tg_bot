import secrets
import redis.asyncio as redis
from loguru import logger
from bot.config import config

DOMAIN = "http://premium-connect.duckdns.org:8080"

# Глобальный клиент Redis для сокращателя ссылок
redis_client = redis.Redis(
    host=config.REDIS_HOST, 
    port=config.REDIS_PORT, 
    db=0, 
    decode_responses=True,
    socket_timeout=5.0
)

async def generate_short_link(long_happ_url: str) -> str:
    """Генерирует короткий ID, сохраняет в Redis и возвращает красивую ссылку"""
    short_id = secrets.token_urlsafe(4) 
    # Сохраняем в Redis на 30 дней (2592000 секунд)
    await redis_client.set(f"shortlink:{short_id}", long_happ_url, ex=2592000)
    return f"{DOMAIN}/v/{short_id}"
