FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates tar && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /tmp/legacy && curl -fsSL --retry 3 'https://github.com/alinenerin/sniper-v9-iqoption/archive/7b2c5eb1250d483ef4f332a9edcf9386f533778e.tar.gz' -o /tmp/legacy/repo.tgz \
    && tar -xzf /tmp/legacy/repo.tgz -C /tmp/legacy \
    && cp -r /tmp/legacy/sniper-v9-iqoption-7b2c5eb1250d483ef4f332a9edcf9386f533778e/iqoptionapi /app/iqoptionapi \
    && rm -rf /tmp/legacy
# The legacy SDK does not pass the proxy to WebSocketApp. Inject the same
# Webshare SOCKS5 route explicitly, while keeping credentials in Railway vars.
RUN python - <<'PY'
from pathlib import Path
p=Path('/app/iqoptionapi/api.py')
s=p.read_text()
old="self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt})"
new="""_proxy_host = os.environ.get('WEBSHARE_SOCKS_HOST', 'socks.webshare.io')
        _proxy_port = int(os.environ.get('WEBSHARE_SOCKS_PORT', '1080'))
        _proxy_user = os.environ.get('WEBSHARE_SOCKS_USERNAME', '')
        _proxy_pass = os.environ.get('WEBSHARE_SOCKS_PASSWORD', '')
        _proxy_kwargs = {'sslopt': _sslopt, 'http_proxy_host': _proxy_host, 'http_proxy_port': _proxy_port, 'proxy_type': 'socks5h'}
        if _proxy_user:
            _proxy_kwargs['http_proxy_auth'] = (_proxy_user, _proxy_pass)
        self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs=_proxy_kwargs)"""
if old not in s: raise SystemExit('SDK pattern missing')
p.write_text(s.replace('import time\n', 'import time\nimport os\n').replace(old,new))
PY
COPY api.py .
COPY core ./core
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} api:app"]
