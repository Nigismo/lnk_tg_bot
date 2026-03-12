import os
import time
import asyncio
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_user, create_user, update_subscription
from bot.keyboards.inline import main_menu_kb, tariffs_kb, payment_methods_kb, vpn_links_kb, check_payment_kb, crypto_pay_kb, main_reply_kb
from services.marzban import marzban_api
from services.happ import happ_service
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
    # Отправляем сначала reply клавиатуру с Web App
    await message.answer("👇 Нажмите кнопку ниже, чтобы открыть красивое приложение:", reply_markup=main_reply_kb())
    # Затем основное меню
    await message.answer(text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "buy_vpn")
async def process_buy_vpn(callback: CallbackQuery):
    """Показ тарифов."""
    await callback.message.edit_text("Выберите подходящий тариф:", reply_markup=tariffs_kb())

@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    text = (
        "👋 Добро пожаловать в лучший VPN сервис!\n\n"
        "🚀 **Стабильное соединение**\n"
        "📺 **4K без лагов**\n"
        "👥 Уже **15 710** пользователей выбрали нас.\n\n"
        "Выберите действие ниже:"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "profile")
async def process_profile(callback: CallbackQuery, session: AsyncSession):
    """Показ профиля пользователя."""
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    status = "🔴 Неактивен"
    if user.sub_end_date and user.sub_end_date > datetime.utcnow():
        days_left = (user.sub_end_date - datetime.utcnow()).days
        status = f"🟢 Активен (осталось {days_left} дней)"

    text = (
        f"👤 **Ваш профиль**\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 Регистрация: {user.registered_at.strftime('%d.%m.%Y')}\n"
        f"📊 Статус подписки: {status}\n"
    )
    
    # Импортируем back_kb здесь, если он еще не импортирован вверху
    from bot.keyboards.inline import back_kb
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "referral")
async def process_referral(callback: CallbackQuery, session: AsyncSession):
    """Показ реферальной программы."""
    user = await get_user(session, callback.from_user.id)
    
    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"
    
    # Подсчет рефералов
    from sqlalchemy import select, func
    from database.models import User
    result = await session.execute(select(func.count(User.id)).where(User.referrer_id == callback.from_user.id))
    referrals_count = result.scalar() or 0
    
    text = (
        f"🎁 **Реферальная программа**\n\n"
        f"Приглашайте друзей и получайте **1 месяц VPN бесплатно** за каждого друга, который оплатит подписку!\n\n"
        f"🔗 Ваша реферальная ссылка:\n`{ref_link}`\n\n"
        f"👥 Приглашено друзей: {referrals_count}"
    )
    
    from bot.keyboards.inline import back_kb
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Выбор тарифа и переход к оплате."""
    tariff_months = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Вы выбрали тариф на {tariff_months} мес.\nВыберите удобный способ оплаты:",
        reply_markup=payment_methods_kb(tariff_months)
    )

async def issue_vpn_access(bot, user_id: int, session: AsyncSession, tariff_months: str):
    """Общая функция выдачи VPN после успешной оплаты."""
    days = TARIFFS[tariff_months]["days"]
    
    status_msg = await bot.send_message(user_id, "⏳ Создание конфигурации VPN...")
    
    username = f"tg_{user_id}"
    expire_ts = int(time.time()) + (days * 86400)
    
    # 1. Создаем пользователя в Marzban
    marzban_user = await marzban_api.create_user(username, expire_ts)
    if not marzban_user:
        await status_msg.edit_text("❌ Ошибка при создании VPN. Обратитесь в поддержку.")
        return
        
    # 2. Достаем обычную ссылку из ответа Marzban
    raw_sub_url = marzban_user.get("subscription_url", "")
    
    # Если Marzban вернул относительную ссылку (например, /sub/12345), делаем её абсолютной
    if raw_sub_url and not raw_sub_url.startswith("http"):
        raw_sub_url = f"{config.MARZBAN_URL.rstrip('/')}{raw_sub_url}"
        
    # 3. МАГИЯ HAPP! Превращаем обычную ссылку в happ://crypt5
    magic_link = await happ_service.encrypt_link(
        raw_url=raw_sub_url, 
        title="Premium_VPN", 
        limit=3  # Лимит на 3 устройства по умолчанию
    )
    
    end_date = datetime.utcnow() + timedelta(days=days)
    await update_subscription(session, user_id, end_date, username, magic_link)
    
    # 4. Отправляем финальную ссылку пользователю
    instruction = (
        "✅ **Оплата прошла успешно! Ваш VPN готов.**\n\n"
        "📱 **Инструкция по подключению:**\n"
        "1. Скачайте приложение HAPP.\n"
        "2. Скопируйте ссылку ниже.\n"
        "3. В приложении нажмите `Добавить из буфера обмена`.\n\n"
        f"Твоя персональная ссылка:\n`{magic_link}`\n\n"
        "У вас доступно 3 устройства одновременно. Приятного использования!"
    )
    await status_msg.edit_text(instruction, reply_markup=vpn_links_kb(magic_link))

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
    
    try:
        import qrcode
        from io import BytesIO
        from aiogram.types import BufferedInputFile
        
        # Ссылка для оплаты или номер телефона (замените на свои данные)
        payment_data = "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79270920073&bankCode=100000000111"
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем в виртуальную память (BytesIO), а не на жесткий диск!
        bio = BytesIO()
        bio.name = 'qr.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        
        photo = BufferedInputFile(bio.read(), filename="payment_qr.png")
        
        # Удаляем старое сообщение, так как мы не можем просто изменить текст на фото
        try:
            await callback.message.delete()
        except:
            pass
            
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=check_payment_kb("sbp", tariff_months)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото СБП: {e}")
        # Если не получилось отправить фото, отправляем просто текст
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            text=text + f"\n\n🔗 [Ссылка для оплаты]({payment_data})",
            reply_markup=check_payment_kb("sbp", tariff_months),
            disable_web_page_preview=False
        )
        
    await callback.answer()

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
        await issue_vpn_access(callback.bot, callback.from_user.id, session, tariff_months)
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
        
    await callback.message.answer(
        "Отлично! Твой платеж на проверке. Обычно это занимает от 1 до 5 минут. Мы пришлем доступ сюда."
    )
    
    # Отправляем уведомление админу
    from bot.keyboards.inline import admin_confirm_payment_kb
    admin_text = (
        f"💰 Юзер @{callback.from_user.username or callback.from_user.id} нажал «Я оплатил».\n"
        f"Тариф: {tariff_months} мес.\n"
        f"Проверь карту. Выдать ему доступ?"
    )
    try:
        await callback.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_text,
            reply_markup=admin_confirm_payment_kb(callback.from_user.id, tariff_months)
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")

    await callback.answer()

@router.message(F.web_app_data)
async def process_web_app_data(message: Message, session: AsyncSession):
    """Обработка данных из Web App."""
    data = message.web_app_data.data
    if data.startswith("webapp_paid_sbp_"):
        tariff_months = data.split("_")[-1]
        
        await message.answer(
            "Отлично! Твой платеж через Web App на проверке. Обычно это занимает от 1 до 5 минут. Мы пришлем доступ сюда."
        )
        
        # Отправляем уведомление админу
        from bot.keyboards.inline import admin_confirm_payment_kb
        admin_text = (
            f"💰 Юзер @{message.from_user.username or message.from_user.id} нажал «Я оплатил» в Web App.\n"
            f"Тариф: {tariff_months} мес.\n"
            f"Проверь карту. Выдать ему доступ?"
        )
        try:
            await message.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=admin_text,
                reply_markup=admin_confirm_payment_kb(message.from_user.id, tariff_months)
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")
