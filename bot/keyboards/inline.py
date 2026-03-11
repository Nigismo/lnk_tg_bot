from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/support")]
    ])

def tariffs_kb() -> InlineKeyboardMarkup:
    """Клавиатура с тарифами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 100 ₽", callback_data="tariff_1")],
        [InlineKeyboardButton(text="3 месяца - 270 ₽", callback_data="tariff_3")],
        [InlineKeyboardButton(text="6 месяцев - 590 ₽", callback_data="tariff_6")],
        [InlineKeyboardButton(text="12 месяцев - 1290 ₽", callback_data="tariff_12")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def payment_methods_kb(tariff: str) -> InlineKeyboardMarkup:
    """Выбор способа оплаты."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Оплата по СБП (QR) - Основной", callback_data=f"pay_sbp_{tariff}")],
        [InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data=f"pay_stars_{tariff}")],
        [InlineKeyboardButton(text="🪙 Криптовалюта", callback_data=f"pay_crypto_{tariff}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_vpn")]
    ])

def check_payment_kb(method: str, tariff: str) -> InlineKeyboardMarkup:
    """Кнопка проверки платежа СБП/Крипто."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_{method}_{tariff}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="buy_vpn")]
    ])

def admin_confirm_payment_kb(user_id: int, tariff: str) -> InlineKeyboardMarkup:
    """Кнопки для админа: подтвердить или отклонить платеж."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выдать VPN", callback_data=f"admin_confirm_pay_{user_id}_{tariff}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_pay_{user_id}")]
    ])

def crypto_pay_kb(pay_url: str, invoice_id: int, tariff: str) -> InlineKeyboardMarkup:
    """Кнопки для оплаты через CryptoBot."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить (CryptoBot / TRC20)", url=pay_url)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_pay_crypto_{invoice_id}_{tariff}")],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="buy_vpn")]
    ])

def vpn_links_kb(sub_url: str) -> InlineKeyboardMarkup:
    """Кнопки с конфигурациями."""

    # Склеиваем твой IP (или домен) с хвостиком подписки. 
    # Если ты уже сделал домен в DuckDNS, впиши его вместо IP! 
    # Например: base_url = "http://premium-connect.duckdns.org:8000"
    base_url = "https://premium-connect.duckdns.org:8000" 

    # Получаем полноценную ссылку для Telegram
    full_url = f"{base_url}{sub_url}"

    # Я обновил названия кнопок под твои реальные мощные протоколы
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Ссылка на подписку (VLESS + SS)", url=full_url)],
        [InlineKeyboardButton(text="❓ Как настроить подключение", callback_data="help_config")]
    ])
