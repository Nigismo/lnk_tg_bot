import asyncio
import secrets
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Импортируем aiohttp для нашего легкого веб-сервера
from aiohttp import web

from bot.config import config
from bot.handlers import user, admin, payments
from bot.middlewares.db import DbSessionMiddleware
from database.models import Base
from services.notifications import check_expiring_subscriptions
from services.shortener import redis_client, generate_short_link

async def redirect_to_vpn(request: web.Request):
    """aiohttp-обработчик: шлюз с красивой страницей вместо белого экрана"""
    short_id = request.match_info.get('short_id')
    long_url = await redis_client.get(f"shortlink:{short_id}")

    if not long_url:
        return web.Response(text="❌ Ошибка 404: Ссылка устарела или не существует", status=404)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Premium Connect</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #0f172a; color: white; text-align: center; padding: 20px; box-sizing: border-box; }}
            .card {{ background: #1e293b; padding: 2rem; border-radius: 1rem; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); max-width: 400px; width: 100%; border: 1px solid #334155; }}
            h2 {{ margin-top: 0; color: #f8fafc; font-size: 1.5rem; }}
            p {{ color: #94a3b8; line-height: 1.5; margin-bottom: 2rem; font-size: 0.95rem; }}
            .btn {{ display: block; background: #3b82f6; color: white; text-decoration: none; padding: 1rem; border-radius: 0.5rem; font-weight: bold; font-size: 1.1rem; transition: background 0.2s; margin-bottom: 1.5rem; }}
            .btn:hover {{ background: #2563eb; }}
            .copy-area {{ background: #0f172a; padding: 1rem; border-radius: 0.5rem; font-size: 0.8rem; color: #64748b; word-break: break-all; border: 1px solid #334155; text-align: left; margin-top: 10px; }}
            .copy-title {{ display: block; margin-top: 1rem; color: #94a3b8; font-weight: bold; text-align: center; font-size: 0.9rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 Ваш VPN готов</h2>
            <p>Нажмите кнопку ниже, чтобы добавить серверы. Приложение HAPP откроется автоматически.</p>

            <a href="{long_url}" class="btn">🔌 Открыть в HAPP</a>

            <span class="copy-title">Или скопируйте ссылку вручную:</span>
            <div class="copy-area">{long_url}</div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

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
