FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd -m appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY watch_bando_unife.py /app/watch_bando_unife.py
# COPY .env /app/.env  # <-- scommenta se vuoi bake-are un .env nel container (di solito meglio passare env dall'host)

RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

ENV DATA_DIR=/app/data

CMD ["python", "/app/watch_bando_unife.py"]
