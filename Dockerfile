FROM python:3.11-slim

WORKDIR /app

# Устанавливаем базовые системные утилиты, которые могут понадобиться для компиляции пакетов
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их напрямую (без кэша, чтобы не раздувать образ)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код проекта
COPY . .

# Запускаем бота
CMD ["python", "-m", "vpn_bot.main"]
