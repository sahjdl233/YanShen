FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GONGKAO_DATA_DIR=/data \
    GONGKAO_HOST=0.0.0.0 \
    GONGKAO_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --gid 1000 yanshen \
    && useradd --uid 1000 --gid yanshen --create-home --shell /usr/sbin/nologin yanshen \
    && mkdir -p /data \
    && chown -R yanshen:yanshen /data

USER yanshen

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{int(os.environ.get(\"GONGKAO_PORT\", \"8000\"))}/health', timeout=3).read()" || exit 1

CMD ["python", "app.py"]
