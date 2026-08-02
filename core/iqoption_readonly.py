"""IQ Option market-data adapter. Read-only by design: no order methods are called."""
import os, time

class IQOptionReadonly:
    def __init__(self):
        self.email = os.getenv('IQ_OPTION_EMAIL', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD', '')
        self.balance_mode = os.getenv('IQ_OPTION_BALANCE_MODE', 'PRACTICE')
        self.connected = False
        self.api = None

    def connect(self):
        if not self.email or not self.password:
            return False, 'IQ_OPTION_CREDENTIALS_NOT_CONFIGURED'
        # The legacy diagnostics used this SOCKS5 Webshare route successfully.
        socks_host = os.getenv('WEBSHARE_SOCKS_HOST', '')
        socks_port = os.getenv('WEBSHARE_SOCKS_PORT', '')
        socks_user = os.getenv('WEBSHARE_SOCKS_USERNAME', '')
        socks_pass = os.getenv('WEBSHARE_SOCKS_PASSWORD', '')
        host, port = os.getenv('WEBSHARE_HOST', ''), os.getenv('WEBSHARE_PORT', '')
        user, pwd = os.getenv('WEBSHARE_USERNAME', ''), os.getenv('WEBSHARE_PASSWORD', '')
        use_socks = bool(socks_host and socks_port)
        try:
            import websocket
            from iqoptionapi.stable_api import IQ_Option
            if use_socks:
                proxy_url = f'socks5h://{socks_user}:{socks_pass}@{socks_host}:{socks_port}'
                os.environ.update({'ALL_PROXY': proxy_url, 'all_proxy': proxy_url})
                if not getattr(websocket.WebSocketApp, '_zapia_proxy_patch', False):
                    original_run_forever = websocket.WebSocketApp.run_forever
                    def run_via_webshare(ws, *args, **kwargs):
                        kwargs.setdefault('http_proxy_host', socks_host)
                        kwargs.setdefault('http_proxy_port', int(socks_port))
                        if socks_user: kwargs.setdefault('http_proxy_auth', (socks_user, socks_pass))
                        kwargs.setdefault('proxy_type', 'socks5')
                        return original_run_forever(ws, *args, **kwargs)
                    websocket.WebSocketApp.run_forever = run_via_webshare
                    websocket.WebSocketApp._zapia_proxy_patch = True
            else:
                proxy_url = f'http://{user}:{pwd}@{host}:{port}' if user and pwd else f'http://{host}:{port}'
                os.environ.update({'HTTP_PROXY': proxy_url, 'HTTPS_PROXY': proxy_url,
                                   'http_proxy': proxy_url, 'https_proxy': proxy_url})
            self.api = IQ_Option(self.email, self.password)
            if hasattr(self.api, 'session'):
                if use_socks:
                    self.api.session.proxies.update({'http': proxy_url, 'https': proxy_url})
                elif host and port:
                    self.api.session.proxies.update({'http': proxy_url, 'https': proxy_url})
            ok, reason = self.api.connect()
            if not ok:
                return False, f'IQ_OPTION_CONNECTION_FAILED:{str(reason or "UNKNOWN")[:120]}'
            self.api.change_balance(self.balance_mode)
            self.connected = True
            return True, 'CONNECTED_READ_ONLY'
        except ImportError:
            return False, 'IQ_OPTION_SDK_IMPORT_FAILED'
        except Exception as exc:
            print(f'IQ Option connection failed: {type(exc).__name__}: {exc}')
            return False, 'IQ_OPTION_CONNECTION_ERROR'

    def candles(self, symbol, interval=60, count=1000):
        if not self.connected:
            ok, reason = self.connect()
            if not ok: return {'ok': False, 'reason': reason}
        symbol = str(symbol).upper().replace('/', '')
        count, interval = max(1, min(int(count), 3000)), int(interval)
        try:
            raw = self.api.get_candles(symbol, interval, count, time.time())
            candles = [{'timestamp': c.get('from'), 'open': c.get('open'), 'high': c.get('max'),
                        'low': c.get('min'), 'close': c.get('close'), 'volume': c.get('volume', 0)} for c in raw or []]
            return {'ok': True, 'symbol': symbol, 'interval_seconds': interval, 'candles': candles,
                    'source': 'IQ_OPTION', 'read_only': True}
        except Exception:
            return {'ok': False, 'reason': 'IQ_OPTION_CANDLES_UNAVAILABLE', 'symbol': symbol}

    def payout(self, symbol):
        if not self.connected:
            ok, reason = self.connect()
            if not ok: return {'ok': False, 'reason': reason}
        symbol = str(symbol).upper().replace('/', '')
        try:
            value = None
            for name in ('get_digital_payout', 'get_binary_payout'):
                fn = getattr(self.api, name, None)
                if callable(fn): value = fn(symbol); break
            return {'ok': value is not None, 'symbol': symbol, 'payout': value,
                    'source': 'IQ_OPTION', 'read_only': True,
                    'reason': None if value is not None else 'PAYOUT_NOT_EXPOSED_BY_SDK'}
        except Exception:
            return {'ok': False, 'reason': 'IQ_OPTION_PAYOUT_UNAVAILABLE', 'symbol': symbol}
