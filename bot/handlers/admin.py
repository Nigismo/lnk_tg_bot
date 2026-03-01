from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.config import config
from services.marzban import marzban_api

router = Router()

# Простой фильтр для админа
def is_admin(message: Message) -> bool:
    return message.from_user.id == config.ADMIN_ID

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель."""
    if not is_admin(message):
        return
    await message.answer("👨‍💻 Админ-панель.\nКоманды:\n/stats - Статистика сервера")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика сервера и онлайна."""
    if not is_admin(message):
        return
        
    stats = await marzban_api.get_system_stats()
    if not stats:
        await message.answer("❌ Ошибка получения статистики Marzban.")
        return
        
    # В Marzban API нет прямого счетчика concurrent users, обычно это берется из Xray
    # Для примера используем заглушку или данные из stats
    active_users = stats.get("active_users", 0)
    total_users = stats.get("total_users", 0)
    
    # Имитация concurrent users
    concurrent = active_users # В реальности нужно парсить метрики Xray
    
    text = (
        f"📊 **Статистика сервера:**\n"
        f"Всего пользователей: {total_users}\n"
        f"Активных подписок: {active_users}\n"
        f"Онлайн (Concurrent): {concurrent} / {config.MAX_CONCURRENT}\n"
    )
    
    if concurrent > config.MAX_CONCURRENT * 0.8:
        text += "\n⚠️ **ВНИМАНИЕ: Нагрузка превышает 80%!**"
        
    await message.answer(text)
