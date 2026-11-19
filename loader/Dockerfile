FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY loader/ .
COPY db/schema.sql .

CMD ["python", "main.py"]