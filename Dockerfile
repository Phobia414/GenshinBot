# ===== БАЗОВЫЙ ОБРАЗ =====
FROM python:3.12-slim

# ===== МЕТАДАННЫЕ =====
LABEL maintainer="@splif1022"
LABEL description="Genshin RPG Bot — Орион"

# ===== НАСТРОЙКИ PYTHON =====
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

# ===== РАБОЧАЯ ДИРЕКТОРИЯ =====
WORKDIR /app

# ===== ЗАВИСИМОСТИ =====
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== КОПИРУЕМ КОД =====
COPY . .

# ===== ЗАПУСК =====
CMD ["python", "main.py"]