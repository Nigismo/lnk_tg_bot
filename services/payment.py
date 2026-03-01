import httpx
from loguru import logger
from bot.config import config

class CryptoPayAPI:
    def __init__(self):
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": config.CRYPTO_PAY_TOKEN}

    async def create_invoice(self, amount: float, asset: str = "USDT", description: str = "") -> dict:
        """Создание счета в CryptoBot."""
        async with httpx.AsyncClient() as client:
            payload = {
                "asset": asset,
                "amount": str(amount),
                "description": description
            }
            response = await client.post(f"{self.base_url}/createInvoice", headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()["result"]

    async def check_invoice(self, invoice_id: int) -> bool:
        """Проверка статуса счета в CryptoBot."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/getInvoices", headers=self.headers, params={"invoice_ids": invoice_id})
            response.raise_for_status()
            invoices = response.json().get("result", {}).get("items", [])
            if invoices and invoices[0]["status"] == "paid":
                return True
            return False

crypto_pay = CryptoPayAPI()

async def create_yookassa_payment(amount: int, description: str, payload: str) -> str:
    """Создание платежа в ЮKassa. Возвращает URL для оплаты."""
    # В реальном проекте здесь интеграция с yookassa API
    logger.info(f"Создан платеж на {amount} руб. Payload: {payload}")
    return "https://yoomoney.ru/checkout/payments/v2/contract?orderId=test"

async def check_yookassa_payment(payment_id: str) -> bool:
    """Проверка статуса платежа."""
    return True
