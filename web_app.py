import secrets
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from bot.config import config

app = FastAPI()

# Подключаемся к Redis асинхронно
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=True)

DOMAIN = "https://premium-connect.duckdns.org"

async def generate_short_link(long_happ_url: str) -> str:
    """Генерирует короткий ID, сохраняет в Redis и возвращает красивую ссылку"""
    short_id = secrets.token_urlsafe(4) 
    
    # Сохраняем в Redis. Живет 30 дней (2592000 секунд)
    await r.set(f"shortlink:{short_id}", long_happ_url, ex=2592000)
    
    return f"{DOMAIN}/v/{short_id}"

@app.get("/v/{short_id}")
async def redirect_to_vpn(short_id: str):
    """Ловит короткую ссылку и редиректит на огромную зашифрованную"""
    long_url = await r.get(f"shortlink:{short_id}")
    
    if not long_url:
        raise HTTPException(status_code=404, detail="Ссылка устарела или не существует")
    
    # HTTP 302 Redirect заставит браузер открыть приложение HAPP или Xray
    return RedirectResponse(url=long_url)
