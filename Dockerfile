FROM python:3.11-slim

WORKDIR /app

# 1. Устанавливаем ВСЕ системные зависимости для компиляции (gcc, g++, python-dev)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 2. Обязательно обновляем инструменты сборки Python перед установкой пакетов
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 3. Устанавливаем наши пакеты
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
