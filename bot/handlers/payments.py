import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.user import issue_vpn_access, TARIFFS

router = Router()

# Функция для расчета цены в Звездах с учетом комиссии Apple/Google (~30%)
# Допустим, 1 звезда = 2 рубля. Чтобы компенсировать 30%, делим цену в рублях на 1.4
def get_stars_price(rub_price: int) -> int:
    return int(rub_price / 1.4)

@router.callback_query(F.data.startswith("pay_stars_"))
async def send_stars_invoice(callback: CallbackQuery, bot: Bot):
    """Отправка инвойса на оплату Звездами"""
    tariff_months = callback.data.split("_")[2]
    rub_price = TARIFFS[tariff_months]["price"]
    stars_price = get_stars_price(rub_price)
    
    prices = [LabeledPrice(label=f"Premium VPN ({tariff_months} мес.)", amount=stars_price)]
    
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"🚀 Premium VPN ({tariff_months} мес.)",
        description="Безлимитный трафик, обход DPI и блокировок рекламы. Быстрая оплата через Telegram Stars.",
        payload=f"vpn_sub_{tariff_months}", # Внутренний ID товара (передаем тариф)
        provider_token="", # ВАЖНО: Для Звезд токен должен быть пустым!
        currency="XTR",    # ВАЖНО: Код валюты Telegram Stars
        prices=prices,
    )
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """
    Обязательный хэндлер. Telegram спрашивает нас: 'Вы готовы выдать товар?'
    Здесь можно проверить доступность серверов Marzban.
    """
    # Подтверждаем готовность принять платеж
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot, session: AsyncSession):
    """Хэндлер успешной оплаты. Деньги списаны, выдаем товар!"""
    payment_info = message.successful_payment
    user_id = message.from_user.id
    payload = payment_info.invoice_payload
    
    logging.info(f"Получена оплата: {payment_info.total_amount} XTR от {user_id}. Payload: {payload}")
    
    if payload.startswith("vpn_sub_"):
        tariff_months = payload.split("_")[2]
        
        # Вызываем общую функцию выдачи VPN из user.py
        # Передаем message, чтобы бот мог ответить на него
        await issue_vpn_access(message, session, message.from_user, tariff_months)
