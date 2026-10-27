FROM python:3.12-slim

# Запобігаємо запису файлів .pyc та вмикаємо миттєвий вивід логів у консоль
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Встановлюємо системні залежності для збирання psycopg та роботи з PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо список залежностей та встановлюємо їх
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копіюємо вихідний код проєкту
COPY . /app/

# Надаємо права на виконання скрипту запуску (якщо використовується окремий entrypoint)
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]