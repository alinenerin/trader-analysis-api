from pathlib import Path
p=Path('/app/iqoptionapi/api.py')
s=p.read_text()
lines=s.splitlines()
out=[]
for line in lines:
    if 'self.websocket_thread = threading.Thread' in line and 'run_forever' in line:
        line="        self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': _sslopt, 'http_proxy_host': os.getenv('WEBSHARE_SOCKS_HOST', '31.59.20.176'), 'http_proxy_port': int(os.getenv('WEBSHARE_SOCKS_PORT', '6754')), 'http_proxy_auth': (os.getenv('WEBSHARE_SOCKS_USERNAME', ''), os.getenv('WEBSHARE_SOCKS_PASSWORD', ''))})"
    out.append(line)
p.write_text('\n'.join(out)+'\n')
