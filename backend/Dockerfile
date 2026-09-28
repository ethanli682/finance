FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

EXPOSE 8000
# `init` is idempotent: creates tables and loads the ticker list on first boot.
CMD ["sh", "-c", "python -m app.cli init && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
