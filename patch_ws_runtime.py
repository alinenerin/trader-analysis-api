from pathlib import Path
p = Path('/app/iqoptionapi/api.py')
s = p.read_text()
old = "self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt})"
new = "self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt, 'http_proxy_host': _os.getenv('WEBSHARE_SOCKS_HOST', '31.59.20.176'), 'http_proxy_port': int(_os.getenv('WEBSHARE_SOCKS_PORT', '6754')), 'http_proxy_auth': (_os.getenv('WEBSHARE_SOCKS_USERNAME', ''), _os.getenv('WEBSHARE_SOCKS_PASSWORD', ''))})"
if old not in s:
    raise SystemExit('SDK run_forever call not found')
p.write_text(s.replace(old, new))
