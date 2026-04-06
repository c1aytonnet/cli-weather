FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY docker ./docker

RUN pip install --no-cache-dir .
RUN chmod +x /app/docker/entrypoint.sh /app/docker/scheduler-entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["cli-weather", "--help"]
