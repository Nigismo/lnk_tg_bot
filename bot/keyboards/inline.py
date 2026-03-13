from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def main_reply_kb() -> ReplyKeyboardMarkup:
    """Нижняя клавиатура."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Купить VPN"), KeyboardButton(text="👤 Мой профиль")]
        ],
        resize_keyboard=True
    )

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Получить 5 дней бесплатно", callback_data="get_trial")],
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="referral")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/support")]
    ])

def back_kb() -> InlineKeyboardMarkup:
    """Кнопка Назад в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
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
        [InlineKeyboardButton(text="📱 Оплата по СБП - Основной", callback_data=f"pay_sbp_{tariff}")],
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

def vpn_links_kb(sub_url: str, short_url: str = None) -> InlineKeyboardMarkup:
    """Кнопки с конфигурациями."""
    buttons = []
    
    if short_url and short_url.startswith("http"):
        buttons.append([InlineKeyboardButton(text="🚀 Подключить в один клик", url=short_url)])
    elif sub_url.startswith("http") or sub_url.startswith("happ://"):
        buttons.append([InlineKeyboardButton(text="🔗 Ссылка на подписку", url=sub_url)])
        
    buttons.append([InlineKeyboardButton(text="❓ Как настроить подключение", callback_data="help_config")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
