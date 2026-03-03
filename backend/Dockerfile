FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY start.sh ./

RUN pip install --no-cache-dir . && chmod +x /app/start.sh

EXPOSE 8000
CMD ["/app/start.sh"]
