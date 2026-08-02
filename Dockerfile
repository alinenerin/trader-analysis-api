FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tar && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY patch_websocket_safe.py /tmp/patch_websocket_safe.py
RUN python3 /tmp/patch_websocket_safe.py
RUN mkdir -p /tmp/legacy && curl -fsSL --retry 3 'https://github.com/alinenerin/sniper-v9-iqoption/archive/7b2c5eb1250d483ef4f332a9edcf9386f533778e.tar.gz' -o /tmp/legacy/repo.tgz \
 && tar -xzf /tmp/legacy/repo.tgz -C /tmp/legacy \
 && cp -r /tmp/legacy/sniper-v9-iqoption-7b2c5eb1250d483ef4f332a9edcf9386f533778e/iqoptionapi /app/iqoptionapi \
 && rm -rf /tmp/legacy
COPY api.py .
COPY core ./core
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} api:app"]
