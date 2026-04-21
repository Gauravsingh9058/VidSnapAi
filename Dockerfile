FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p /var/data/uploads /app/instance

EXPOSE 10000

CMD ["/bin/sh", "-c", "gunicorn --worker-class gthread --workers 1 --threads ${GUNICORN_THREADS:-8} --timeout ${GUNICORN_TIMEOUT:-300} --bind 0.0.0.0:${PORT:-10000} main:app"]
