import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.config import config
from bot.handlers import user, admin
from bot.middlewares.db import DbSessionMiddleware
from database.models import Base
from services.notifications import check_expiring_subscriptions
from services.ip_limiter import ip_limiter

async def main():
    logger.info("Запуск VPN бота...")
    
    # Инициализация БД
    engine = create_async_engine(config.db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp = Dispatcher()
    
    # Регистрация middlewares
    dp.update.middleware(DbSessionMiddleware(session_maker))
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(user.router)
    
    # Запуск фоновых задач
    asyncio.create_task(check_expiring_subscriptions(bot, session_maker))
    asyncio.create_task(ip_limiter.tail_logs())
    
    # Запуск polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
