import urllib.parse
from loguru import logger
from services.shortener import generate_short_link


class HappService:
    async def create_premium_link(self, raw_url: str, title: str = "🇺🇸 Premium VPN") -> tuple[str, str]:
        """
        Создает нашу собственную мощную ссылку с обходом DPI и сокращает её.
        Возвращает кортеж: (длинная_ссылка_с_dpi, короткая_ссылка)
        """
        try:
            # 1. Вшиваем обход DPI (fragment) напрямую в ссылку согласно докам HAPP
            params = {"fragment": "1-10,5-20,tlshello"}
            query_string = urllib.parse.urlencode(params, safe=',')

            # 2. Добавляем эстетику (Название и иконки)
            safe_title = urllib.parse.quote(title)

            # 3. Собираем ФИНАЛЬНУЮ ссылку (Формат: URL#Title?Params)
            complex_url = f"{raw_url}#{safe_title}?{query_string}"

            # 4. Сокращаем ссылку через наш уже готовый локальный Redis-сервис
            short_url = await generate_short_link(complex_url)

            logger.info(f"✅ Сгенерирована локальная ссылка: {short_url}")
            return complex_url, short_url

        except Exception as e:
            logger.error(f"❌ Ошибка генерации ссылки: {e}")
            return raw_url, raw_url  # В случае ошибки отдаем то, что есть


happ_service = HappService()
