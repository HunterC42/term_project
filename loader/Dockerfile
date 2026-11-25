FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY loader/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY loader/ ./loader/
COPY db/ ./db/

CMD ["python", "loader/main.py"]
