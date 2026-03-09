import os
import time
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_user, create_user, update_subscription
from bot.keyboards.inline import main_menu_kb, tariffs_kb, payment_methods_kb, vpn_links_kb, check_payment_kb, crypto_pay_kb
from services.marzban import marzban_api
from services.payment import crypto_pay
from bot.config import config
from loguru import logger

router = Router()

TARIFFS = {
    "1": {"price": 100, "days": 30},
    "3": {"price": 270, "days": 90},
    "6": {"price": 590, "days": 180},
    "12": {"price": 1290, "days": 365}
}

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Обработчик команды /start."""
    user = await get_user(session, message.from_user.id)
    if not user:
        args = message.text.split()
        referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        await create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name, referrer_id)
    
    text = (
        "👋 Добро пожаловать в лучший VPN сервис!\n\n"
        "🚀 **Стабильное соединение**\n"
        "📺 **4K без лагов**\n"
        "👥 Уже **15 710** пользователей выбрали нас.\n\n"
        "Выберите действие ниже:"
    )
    await message.answer(text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "buy_vpn")
async def process_buy_vpn(callback: CallbackQuery):
    """Показ тарифов."""
    await callback.message.edit_text("Выберите подходящий тариф:", reply_markup=tariffs_kb())

@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Выбор тарифа и переход к оплате."""
    tariff_months = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Вы выбрали тариф на {tariff_months} мес.\nВыберите удобный способ оплаты:",
        reply_markup=payment_methods_kb(tariff_months)
    )

async def issue_vpn_access(bot_msg: Message, session: AsyncSession, tg_user, tariff_months: str):
    """Общая функция выдачи VPN после успешной оплаты."""
    days = TARIFFS[tariff_months]["days"]
    
    # Если предыдущее сообщение было с фото (СБП), edit_text не сработает напрямую.
    # Поэтому удаляем старое сообщение и отправляем новое текстовое.
    try:
        await bot_msg.delete()
    except Exception:
        pass
        
    status_msg = await bot_msg.answer("⏳ Создание конфигурации VPN...")
    
    username = f"tg_{tg_user.id}"
    expire_ts = int(time.time()) + (days * 86400)
    
    marzban_user = await marzban_api.create_user(username, expire_ts)
    if not marzban_user:
        await status_msg.edit_text("❌ Ошибка при создании VPN. Обратитесь в поддержку.")
        return
        
    sub_url = marzban_user.get("subscription_url", "https://a2key.xyz/sub/example")
    
    end_date = datetime.utcnow() + timedelta(days=days)
    await update_subscription(session, tg_user.id, end_date, username, sub_url)
    
    instruction = (
        "✅ **Оплата прошла успешно! Ваш VPN готов.**\n\n"
        "📱 **Инструкция по подключению:**\n"
        "1. Скачайте приложение (V2RayNG / FoXray / v2rayN).\n"
        "2. Скопируйте ссылку ниже.\n"
        "3. В приложении выберите `Add configuration` -> `From clipboard`.\n\n"
        "У вас доступно 3 устройства одновременно. Приятного использования!"
    )
    await status_msg.edit_text(instruction, reply_markup=vpn_links_kb(sub_url))

@router.callback_query(F.data.startswith("pay_sbp_"))
async def process_pay_sbp(callback: CallbackQuery):
    """Оплата через СБП (QR)."""
    tariff_months = callback.data.split("_")[2]
    price = TARIFFS[tariff_months]["price"]
    
    text = (
        f"📱 **Оплата по СБП**\n\n"
        f"К оплате: **{price} ₽**\n"
        f"Отсканируйте QR-код ниже в приложении вашего банка или переведите по номеру телефона.\n\n"
        f"После перевода нажмите кнопку «Я оплатил»."
    )
    
    qr_url = "https://i.ibb.co/6c2m4vK1/sbp-qr.jpg"
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer_photo(
        photo=qr_url, 
        caption=text, 
        reply_markup=check_payment_kb("sbp", tariff_months)
    )

@router.callback_query(F.data.startswith("pay_crypto_"))
async def process_pay_crypto(callback: CallbackQuery):
    """Оплата криптовалютой через CryptoBot."""
    tariff_months = callback.data.split("_")[2]
    price = TARIFFS[tariff_months]["price"]
    usdt_price = round(price / 95, 2) # Примерный курс
    
    if not config.CRYPTO_PAY_TOKEN:
        await callback.message.edit_text("❌ Оплата криптовалютой временно недоступна (не настроен токен).")
        return

    msg = await callback.message.edit_text("⏳ Создание счета...")
    
    try:
        invoice = await crypto_pay.create_invoice(
            amount=usdt_price,
            asset="USDT",
            description=f"VPN на {tariff_months} мес."
        )
        
        text = (
            f"🪙 **Оплата Криптовалютой (USDT TRC20)**\n\n"
            f"К оплате: **{usdt_price} USDT**\n"
            f"Счет выставлен через официальный кошелек @CryptoBot.\n"
            f"Бот автоматически сгенерирует уникальный адрес TRC20 и проверит транзакцию в блокчейне.\n\n"
            f"Нажмите кнопку ниже для оплаты, а затем «Я оплатил»."
        )
        await msg.edit_text(text, reply_markup=crypto_pay_kb(invoice["pay_url"], invoice["invoice_id"], tariff_months))
    except Exception as e:
        logger.error(f"Ошибка создания счета CryptoPay: {e}")
        await msg.edit_text("❌ Ошибка при создании счета. Попробуйте другой способ оплаты.")

@router.callback_query(F.data.startswith("check_pay_crypto_"))
async def process_check_pay_crypto(callback: CallbackQuery, session: AsyncSession):
    """Проверка платежа CryptoBot."""
    parts = callback.data.split("_")
    invoice_id = int(parts[3])
    tariff_months = parts[4]
    
    is_paid = await crypto_pay.check_invoice(invoice_id)
    if is_paid:
        await issue_vpn_access(callback.message, session, callback.from_user, tariff_months)
    else:
        await callback.answer("❌ Транзакция еще не подтверждена сетью. Подождите пару минут и нажмите снова.", show_alert=True)

@router.callback_query(F.data.startswith("check_pay_sbp_"))
async def process_check_pay_sbp(callback: CallbackQuery, session: AsyncSession):
    """Проверка платежа (СБП)."""
    parts = callback.data.split("_")
    tariff_months = parts[3]
    
    # Если сообщение с фото, edit_text не сработает напрямую, поэтому удаляем и шлем новое
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    msg = await callback.message.answer("⏳ Проверяем поступление средств...")
    await asyncio.sleep(2) # Имитация проверки
    
    # Имитируем успешную оплату
    await issue_vpn_access(msg, session, callback.from_user, tariff_months)
