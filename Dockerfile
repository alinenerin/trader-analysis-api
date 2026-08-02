FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tar && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /tmp/legacy && curl -fsSL --retry 3 'https://github.com/alinenerin/sniper-v9-iqoption/archive/refs/heads/main.tar.gz' -o /tmp/legacy/repo.tgz \
    && tar -xzf /tmp/legacy/repo.tgz -C /tmp/legacy \
    && cp -r /tmp/legacy/sniper-v9-iqoption-main/iqoptionapi /app/iqoptionapi \
    && rm -rf /tmp/legacy
COPY api.py .
COPY core ./core
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} api:app"]
