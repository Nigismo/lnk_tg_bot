import asyncio
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.config import config
from bot.handlers import user, admin, payments
from bot.middlewares.db import DbSessionMiddleware
from database.models import Base
from services.notifications import check_expiring_subscriptions
from services.ip_limiter import ip_limiter

async def main():
    logger.info("Запуск VPN бота...")
    
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
            # Проверяем существование таблиц
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
    asyncio.create_task(ip_limiter.tail_logs())
    
    # Запуск FastAPI сервера для коротких ссылок
    import uvicorn
    from web_app import app as fastapi_app
    uvicorn_config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    uvicorn_server = uvicorn.Server(uvicorn_config)
    asyncio.create_task(uvicorn_server.serve())
    
    # Запуск polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
