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
        referrer_id = None
        if len(args) > 1:
            ref_arg = args[1]
            if ref_arg.startswith("ref_"):
                ref_arg = ref_arg[4:]
            if ref_arg.isdigit():
                referrer_id = int(ref_arg)
        await create_user(session, message.from_user.id, message.from_user.username, message.from_user.full_name, referrer_id)
        if referrer_id:
            try:
                await message.bot.send_message(referrer_id, "🎉 По вашей ссылке зарегистрировался новый пользователь!")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление рефереру: {e}")
    
    text = (
        "👋 *Добро пожаловать в Premium Connect!*\n\n"
        "Мы предоставляем быстрый и безопасный VPN с защитой от блокировок (DPI) "
        "и поддержкой всех современных устройств.\n\n"
        "Выберите действие ниже 👇"
    )
    # Отправляем сначала reply клавиатуру с Web App
    await message.answer("👇 Нажмите кнопку ниже, чтобы открыть красивое приложение:", reply_markup=main_reply_kb())
    # Затем основное меню
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "buy_vpn")
async def process_buy_vpn(callback: CallbackQuery):
    """Показ тарифов."""
    await callback.message.edit_text("Выберите подходящий тариф:", reply_markup=tariffs_kb())

@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    text = (
        "👋 *Добро пожаловать в Premium Connect!*\n\n"
        "Мы предоставляем быстрый и безопасный VPN с защитой от блокировок (DPI) "
        "и поддержкой всех современных устройств.\n\n"
        "Выберите действие ниже 👇"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "profile")
async def process_profile(callback: CallbackQuery, session: AsyncSession):
    """Показ профиля пользователя."""
    user = await get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    status = "🔴 Неактивен"
    if user.sub_end_date and user.sub_end_date > datetime.utcnow():
        time_left = user.sub_end_date - datetime.utcnow()
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        
        if days_left > 0:
            left_str = f"{days_left} дн."
        else:
            left_str = f"{hours_left} ч."

        if user.marzban_username and user.marzban_username.endswith("_trial"):
            status = f"🎁 Тестовый период (осталось {left_str})"
        else:
            status = f"🟢 Активен (осталось {left_str})"

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📅 Регистрация: {user.registered_at.strftime('%d.%m.%Y')}\n"
        f"📊 Статус подписки: {status}\n"
    )
    
    # Импортируем back_kb здесь, если он еще не импортирован вверху
    from bot.keyboards.inline import back_kb
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")

@router.callback_query(F.data == "referral")
async def process_referral(callback: CallbackQuery, session: AsyncSession):
    """Показ реферальной программы."""
    user = await get_user(session, callback.from_user.id)
    
    bot_info = await callback.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    
    # Подсчет рефералов
    from sqlalchemy import select, func
    from database.models import User
    result = await session.execute(select(func.count(User.id)).where(User.referrer_id == callback.from_user.id))
    referrals_count = result.scalar() or 0
    earned_days = referrals_count * 15
    
    text = (
        "🎁 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте бесплатный VPN!\n"
        "За каждого друга, который оплатит любую подписку, вы получите *+15 дней* к вашему тарифу, "
        "а ваш друг получит скидку 10% на первую покупку.\n\n"
        f"🔗 *Ваша персональная ссылка:*\n`{ref_link}`\n\n"
        f"👥 Приглашено друзей: *{referrals_count}*\n"
        f"⏳ Получено дней: *{earned_days}*"
    )
    
    import urllib.parse
    share_text = urllib.parse.quote("Привет! Пользуюсь этим премиум VPN, работает без перебоев. Держи ссылку!")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    share_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Поделиться с другом", url=f"https://t.me/share/url?url={ref_link}&text={share_text}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=share_kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: CallbackQuery):
    """Выбор тарифа и переход к оплате."""
    tariff_months = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Вы выбрали тариф на {tariff_months} мес.\nВыберите удобный способ оплаты:",
        reply_markup=payment_methods_kb(tariff_months)
    )

@router.callback_query(F.data == "get_trial")
async def process_get_trial(callback: CallbackQuery, session: AsyncSession):
    """Выдача бесплатного тестового периода на 5 дней."""
    user_id = callback.from_user.id
    
    # 1. Защита от абуза: проверяем, брал ли юзер уже VPN
    user = await get_user(session, user_id)
    if user and user.marzban_username:
        await callback.answer(
            "❌ Вы уже использовали тестовый период или у вас есть подписка.", 
            show_alert=True
        )
        return

    status_msg = await callback.message.edit_text("⏳ Генерируем ваши персональные ключи доступа...")
    
    # 2. Настройки триала (5 дней)
    days = 5
    username = f"tg_{user_id}_trial"
    expire_ts = int(time.time()) + (days * 86400)
    
    # 3. Создаем юзера в Marzban
    marzban_user = await marzban_api.create_user(username, expire_ts)
    if not marzban_user:
        await status_msg.edit_text("❌ Ошибка при выдаче триала. Сервер недоступен.")
        return
        
    # Достаем ссылку (если Marzban отдает относительную - склеиваем с доменом)
    sub_url = marzban_user.get("subscription_url", "")
    if not sub_url and marzban_user.get("links"):
        sub_url = marzban_user.get("links")[0]
        
    if sub_url and not sub_url.startswith("http") and not sub_url.startswith("vless://") and not sub_url.startswith("vmess://") and not sub_url.startswith("trojan://") and not sub_url.startswith("ss://"):
        sub_url = f"{config.MARZBAN_URL.rstrip('/')}{sub_url}"
        
    # Используем HAPP для шифрования ссылки
    sub_url = await happ_service.encrypt_link(sub_url, title="🎁_Trial", limit=3)
    
    # Сокращаем ссылку для красивой кнопки
    short_url = await happ_service.shorten_url(sub_url)
    
    # 4. Записываем в базу данных, что юзер получил доступ
    end_date = datetime.utcnow() + timedelta(days=days)
    await update_subscription(session, user_id, end_date, username, sub_url)
    
    # 5. Выдаем ссылку
    instruction = (
        "🎁 <b>Тестовый период успешно активирован!</b>\n\n"
        "У вас есть ровно 5 дней максимальной скорости, чтобы оценить качество нашего Premium VPN.\n\n"
        "📱 <b>Как подключиться:</b>\n"
        "1. Скачайте приложение HAPP.\n"
    )
    
    if short_url.startswith("http"):
        instruction += (
            "2. Нажмите кнопку <b>«🚀 Подключить в один клик»</b> ниже.\n"
            "3. Разрешите открыть конфигурацию в приложении."
        )
    else:
        instruction += (
            "2. Скопируйте ключ доступа ниже.\n"
            "3. В приложении нажмите <code>Добавить из буфера обмена</code>.\n\n"
            "<blockquote expandable><b>Ваш ключ доступа (нажмите для копирования):</b>\n"
            f"<code>{sub_url}</code></blockquote>"
        )
    
    try:
        await status_msg.edit_text(instruction, reply_markup=vpn_links_kb(sub_url, short_url), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending trial link: {e}")
        await status_msg.edit_text(instruction, parse_mode="HTML")

async def issue_vpn_access(bot, user_id: int, session: AsyncSession, tariff_months: str):
    """Общая функция выдачи VPN после успешной оплаты."""
    days = TARIFFS[tariff_months]["days"]
    
    status_msg = await bot.send_message(user_id, "⏳ Создание конфигурации VPN...")
    
    username = f"tg_{user_id}"
    
    # Получаем пользователя из БД
    user = await get_user(session, user_id)
    is_first_payment = user and user.sub_end_date is None
    
    # Считаем новую дату окончания
    now = datetime.utcnow()
    if user and user.sub_end_date and user.sub_end_date > now:
        end_date = user.sub_end_date + timedelta(days=days)
    else:
        end_date = now + timedelta(days=days)
        
    expire_ts = int(end_date.timestamp())
    
    # 1. Создаем или обновляем пользователя в Marzban
    marzban_user = await marzban_api.get_user(username)
    if marzban_user:
        # Обновляем
        marzban_user = await marzban_api.update_user(username, expire=expire_ts, status="active")
    else:
        # Создаем
        marzban_user = await marzban_api.create_user(username, expire_ts)
        
    if not marzban_user:
        await status_msg.edit_text("❌ Ошибка при создании/обновлении VPN. Обратитесь в поддержку.")
        return
        
    # 2. Достаем обычную ссылку из ответа Marzban
    raw_sub_url = marzban_user.get("subscription_url", "")
    if not raw_sub_url and marzban_user.get("links"):
        raw_sub_url = marzban_user.get("links")[0]
    
    # Если Marzban вернул относительную ссылку (например, /sub/12345), делаем её абсолютной
    if raw_sub_url and not raw_sub_url.startswith("http") and not raw_sub_url.startswith("vless://") and not raw_sub_url.startswith("vmess://") and not raw_sub_url.startswith("trojan://") and not raw_sub_url.startswith("ss://"):
        raw_sub_url = f"{config.MARZBAN_URL.rstrip('/')}{raw_sub_url}"
        
    # 3. МАГИЯ HAPP! Превращаем обычную ссылку в happ://crypt5
    magic_link = await happ_service.encrypt_link(
        raw_url=raw_sub_url, 
        title="🇺🇸 Premium VPN", 
        limit=3  # Лимит на 3 устройства по умолчанию
    )
    
    # Сокращаем ссылку для красивой кнопки
    short_magic_link = await happ_service.shorten_url(magic_link)
    
    await update_subscription(session, user_id, end_date, username, magic_link)
    
    # 4. Отправляем финальную ссылку пользователю
    instruction = (
        "✅ <b>Оплата прошла успешно! Ваш VPN готов.</b>\n\n"
        "📱 <b>Инструкция по подключению:</b>\n"
        "1. Скачайте приложение HAPP.\n"
    )
    
    if short_magic_link.startswith("http"):
        instruction += (
            "2. Нажмите кнопку <b>«🚀 Подключить в один клик»</b> ниже.\n"
            "3. Разрешите открыть конфигурацию в приложении.\n\n"
            "У вас доступно 3 устройства одновременно. Приятного использования!"
        )
    else:
        instruction += (
            "2. Скопируйте ключ доступа ниже.\n"
            "3. В приложении нажмите <code>Добавить из буфера обмена</code>.\n\n"
            "<blockquote expandable><b>Ваш ключ доступа (нажмите для копирования):</b>\n"
            f"<code>{magic_link}</code></blockquote>\n\n"
            "У вас доступно 3 устройства одновременно. Приятного использования!"
        )
        
    try:
        await status_msg.edit_text(instruction, reply_markup=vpn_links_kb(magic_link, short_magic_link), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error sending paid link: {e}")
        await status_msg.edit_text(instruction, parse_mode="HTML")
    
    # 5. Начисление бонуса рефереру
    if is_first_payment and user and user.referrer_id:
        referrer = await get_user(session, user.referrer_id)
        if referrer:
            ref_days = 15 # Бонус 15 дней
            ref_now = datetime.utcnow()
            if referrer.sub_end_date and referrer.sub_end_date > ref_now:
                ref_end_date = referrer.sub_end_date + timedelta(days=ref_days)
            else:
                ref_end_date = ref_now + timedelta(days=ref_days)
                
            ref_username = f"tg_{referrer.id}"
            ref_expire_ts = int(ref_end_date.timestamp())
            
            ref_marzban_user = await marzban_api.get_user(ref_username)
            if ref_marzban_user:
                ref_marzban_user = await marzban_api.update_user(ref_username, expire=ref_expire_ts, status="active")
            else:
                ref_marzban_user = await marzban_api.create_user(ref_username, ref_expire_ts)
                
            if ref_marzban_user:
                ref_raw_sub_url = ref_marzban_user.get("subscription_url", "")
                if not ref_raw_sub_url and ref_marzban_user.get("links"):
                    ref_raw_sub_url = ref_marzban_user.get("links")[0]
                if ref_raw_sub_url and not ref_raw_sub_url.startswith("http") and not ref_raw_sub_url.startswith("vless://") and not ref_raw_sub_url.startswith("vmess://") and not ref_raw_sub_url.startswith("trojan://") and not ref_raw_sub_url.startswith("ss://"):
                    ref_raw_sub_url = f"{config.MARZBAN_URL.rstrip('/')}{ref_raw_sub_url}"
                ref_magic_link = await happ_service.encrypt_link(ref_raw_sub_url, "🇺🇸 Premium VPN", 3)
                
                await update_subscription(session, referrer.id, ref_end_date, ref_username, ref_magic_link)
                
                try:
                    await bot.send_message(
                        referrer.id,
                        "🎉 <b>Отличные новости!</b>\n\n"
                        "Ваш друг только что оплатил подписку! 🎁\n"
                        f"Вам начислено <b>+{ref_days} дней</b> бесплатного VPN.\n"
                        "Спасибо, что рекомендуете нас!",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Error sending referrer bonus message: {e}")

@router.callback_query(F.data.startswith("pay_sbp_"))
async def process_pay_sbp(callback: CallbackQuery):
    """Оплата через СБП (По ссылке)."""
    tariff_months = callback.data.split("_")[2]
    price = TARIFFS[tariff_months]["price"]
    
    payment_link = "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79270920073&bankCode=100000000111"
    short_payment_link = await happ_service.shorten_url(payment_link)
    
    text = (
        f"📱 <b>Оплата по СБП</b>\n\n"
        f"К оплате: <b>{price} ₽</b>\n\n"
        f"Для оплаты перейдите по ссылке ниже.\n"
        f"После перевода обязательно нажмите кнопку «Я оплатил»."
    )
    
    # Создаем клавиатуру с кнопкой для оплаты и кнопкой проверки
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить (Сбербанк / СБП)", url=short_payment_link)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_sbp_{tariff_months}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="buy_vpn")]
    ])
    
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка отправки СБП: {e}")
        
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
            reply_markup=admin_confirm_payment_kb(callback.from_user.id, tariff_months),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")

    await callback.answer()

@router.message(F.text == "🛒 Купить VPN")
async def handle_buy_vpn_text(message: Message):
    """Обработка текстовой кнопки Купить VPN."""
    from bot.keyboards.inline import tariffs_kb
    await message.answer(
        "🛒 <b>Выберите тарифный план:</b>\n\n"
        "Чем больше период, тем выгоднее цена!",
        reply_markup=tariffs_kb(),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 Мой профиль")
async def handle_profile_text(message: Message, session: AsyncSession):
    """Обработка текстовой кнопки Мой профиль."""
    user = await get_user(session, message.from_user.id)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    status = "🔴 Неактивен"
    if user.sub_end_date and user.sub_end_date > datetime.utcnow():
        time_left = user.sub_end_date - datetime.utcnow()
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        
        if days_left > 0:
            left_str = f"{days_left} дн."
        else:
            left_str = f"{hours_left} ч."

        if user.marzban_username and user.marzban_username.endswith("_trial"):
            status = f"🎁 Тестовый период (осталось {left_str})"
        else:
            status = f"🟢 Активен (осталось {left_str})"

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📅 Регистрация: {user.registered_at.strftime('%d.%m.%Y')}\n"
        f"📊 Статус подписки: {status}\n"
    )
    
    from bot.keyboards.inline import back_kb
    await message.answer(text, reply_markup=back_kb(), parse_mode="HTML")
