from pathlib import Path
p=Path('/app/iqoptionapi/api.py')
s=p.read_text()
old="self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt})"
new="self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt, 'http_proxy_host': os.getenv('WEBSHARE_SOCKS_HOST', '31.59.20.176'), 'http_proxy_port': int(os.getenv('WEBSHARE_SOCKS_PORT', '6754')), 'http_proxy_auth': (os.getenv('WEBSHARE_SOCKS_USERNAME', ''), os.getenv('WEBSHARE_SOCKS_PASSWORD', ''))})"
if old in s:
    p.write_text(s.replace(old,new))
else:
    print('websocket target differs; leaving SDK unchanged')
