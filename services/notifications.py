import asyncio
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_active_users
from aiogram import Bot

async def check_expiring_subscriptions(bot: Bot, session_maker):
    """Фоновая задача для проверки истекающих подписок (каждые 6 часов)."""
    while True:
        try:
            async with session_maker() as session:
                users = await get_active_users(session)
                now = datetime.utcnow()
                
                for user in users:
                    if not user.sub_end_date:
                        continue
                        
                    time_left = user.sub_end_date - now
                    
                    # Уведомление за 3 дня
                    if timedelta(days=2, hours=18) < time_left <= timedelta(days=3):
                        try:
                            await bot.send_message(user.id, "⚠️ Ваша подписка истекает через 3 дня! Продлите, чтобы оставаться на связи.")
                        except Exception as e:
                            logger.error(f"Не удалось отправить уведомление {user.id}: {e}")
                            
                    # Уведомление за 1 день
                    elif timedelta(hours=18) < time_left <= timedelta(days=1):
                        try:
                            await bot.send_message(user.id, "🚨 Ваша подписка истекает завтра! Успейте продлить.")
                        except Exception as e:
                            logger.error(f"Не удалось отправить уведомление {user.id}: {e}")
                            
        except Exception as e:
            logger.error(f"Ошибка в задаче проверки подписок: {e}")
            
        await asyncio.sleep(6 * 3600) # 6 часов
