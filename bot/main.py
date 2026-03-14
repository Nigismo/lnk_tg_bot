import asyncio
import secrets
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Импортируем aiohttp для нашего легкого веб-сервера
from aiohttp import web
import redis.asyncio as redis

from bot.config import config
from bot.handlers import user, admin, payments
from bot.middlewares.db import DbSessionMiddleware
from database.models import Base
from services.notifications import check_expiring_subscriptions

DOMAIN = "https://premium-connect.duckdns.org"

# Глобальный клиент Redis для сокращателя ссылок
redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, decode_responses=True)

async def generate_short_link(long_happ_url: str) -> str:
    """Генерирует короткий ID, сохраняет в Redis и возвращает красивую ссылку"""
    short_id = secrets.token_urlsafe(4) 
    # Сохраняем в Redis на 30 дней (2592000 секунд)
    await redis_client.set(f"shortlink:{short_id}", long_happ_url, ex=2592000)
    return f"{DOMAIN}/v/{short_id}"

async def redirect_to_vpn(request: web.Request):
    """aiohttp-обработчик: ловит короткую ссылку и делает редирект"""
    short_id = request.match_info.get('short_id')
    long_url = await redis_client.get(f"shortlink:{short_id}")
    
    if not long_url:
        return web.Response(text="❌ Ссылка устарела или не существует", status=404)
    
    # HTTP 302 Redirect на огромную зашифрованную ссылку HAPP
    raise web.HTTPFound(long_url)

async def start_web_server():
    """Запускает встроенный aiohttp сервер"""
    app = web.Application()
    app.router.add_get('/v/{short_id}', redirect_to_vpn)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # ⚠️ ВАЖНО: Используем порт 8080, чтобы не конфликтовать с Marzban (8000)
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("🌐 Встроенный веб-сервер для редиректов запущен на порту 8080")

async def main():
    logger.info("🚀 Запуск VPN бота...")
    
    # Инициализация БД
    engine = create_async_engine(config.db_url, echo=False)
    
    # Запуск миграций Alembic
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    async def check_and_run_migrations():
        def run_upgrade():
            command.upgrade(alembic_cfg, "head")
            
        def run_stamp():
            command.stamp(alembic_cfg, "head")

        async with engine.connect() as conn:
            def check_tables(connection):
                from sqlalchemy import inspect
                inspector = inspect(connection)
                return inspector.get_table_names()
                
            tables = await conn.run_sync(check_tables)
            
            if "users" in tables and "alembic_version" not in tables:
                logger.info("Таблицы уже существуют. Делаем stamp head...")
                await asyncio.to_thread(run_stamp)
            else:
                logger.info("Применение миграций БД...")
                await asyncio.to_thread(run_upgrade)
                
    await check_and_run_migrations()
        
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp = Dispatcher()
    
    # Регистрация middlewares
    dp.update.middleware(DbSessionMiddleware(session_maker))
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(payments.router)
    
    # Запуск фоновых задач
    asyncio.create_task(check_expiring_subscriptions(bot, session_maker))
    
    # Запуск встроенного веб-сервера для коротких ссылок
    await start_web_server()
    
    # Запуск polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())
