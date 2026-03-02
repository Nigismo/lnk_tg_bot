FROM python:3.11

WORKDIR /app

# Копируем список библиотек
COPY requirements.txt .

# Обновляем установщики
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бота
COPY . .

# Запускаем бота (если main.py лежит внутри папки vpn_bot)
CMD ["python", "-m", "bot.main"]
