FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY extract/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY extract/ ./extract/

CMD ["python", "extract/extract.py"]
