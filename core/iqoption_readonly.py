"""Persistent read-only IQ Option session using the current Webshare direct proxy."""
import os
import time
import threading

_client = None
_state = {'status': 'starting', 'reason': None, 'connected_at': None}
_lock = threading.RLock()
_start_once = False
_patched = False

class IQOptionReadonly:
    def __init__(self):
        global _client, _start_once
        self.email = os.getenv('IQ_OPTION_EMAIL') or os.getenv('IQ_USER', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD') or os.getenv('IQ_PASS', '')
        self.balance_mode = os.getenv('IQ_OPTION_BALANCE_MODE') or os.getenv('BALANCE_MODE', 'PRACTICE')
        self.connected = False
        self.api = None
        with _lock:
            if _client is not None:
                self.api, self.connected = _client.api, bool(_client.api)
            if not _start_once:
                _start_once = True
                threading.Thread(target=self._connect_worker, daemon=True, name='iqoption-session').start()

    def _connect_worker(self):
        global _client, _state, _patched
        with _lock:
            if self.api and self.connected: return
            if not self.email or not self.password:
                _state.update(status='error', reason='IQ_OPTION_CREDENTIALS_NOT_CONFIGURED'); return
            _state.update(status='connecting', reason=None)
        try:
            from iqoptionapi.stable_api import IQ_Option
            import websocket
            host = os.getenv('WEBSHARE_SOCKS_HOST', '45.38.107.97')
            port = int(os.getenv('WEBSHARE_SOCKS_PORT', '6014'))
            user = os.getenv('WEBSHARE_SOCKS_USERNAME', 'gjgztyys')
            pwd = os.getenv('WEBSHARE_SOCKS_PASSWORD', '')
            proxy_url = f'http://{user}:{pwd}@{host}:{port}'
            # The old working Railway runner used proxy environment variables;
            # the SDK HTTP session must also receive the same route.
            for key in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):
                os.environ[key] = proxy_url
            original = websocket.WebSocketApp.run_forever
            if not _patched:
                def proxied(ws, *args, **kwargs):
                    kwargs.setdefault('http_proxy_host', host)
                    kwargs.setdefault('http_proxy_port', port)
                    kwargs.setdefault('proxy_type', 'http')
                    kwargs.setdefault('http_proxy_auth', (user, pwd))
                    return original(ws, *args, **kwargs)
                websocket.WebSocketApp.run_forever = proxied
                _patched = True
            api = IQ_Option(self.email, self.password)
            # Force the REST login through the same verified Webshare endpoint.
            if hasattr(api, 'session'):
                api.session.proxies.update({'http': proxy_url, 'https': proxy_url})
            ok, reason = api.connect()
            if not ok:
                _state.update(status='error', reason=str(reason or 'IQ_OPTION_LOGIN_FAILED')[:180]); return
            try: api.change_balance(self.balance_mode)
            except Exception: pass
            with _lock:
                self.api, self.connected, _client = api, True, self
                _state.update(status='connected', reason=None, connected_at=time.time())
        except Exception as exc:
            _state.update(status='error', reason=f'{type(exc).__name__}: {exc}'[:180])

    def connect(self):
        if self.connected and self.api: return True, 'CONNECTED_READ_ONLY'
        return False, _state.get('reason') or 'IQ_OPTION_CONNECTING'

    def candles(self, symbol, interval=60, count=1000):
        if not self.connected or not self.api:
            return {'ok': False, 'reason': _state.get('reason') or 'IQ_OPTION_CONNECTING', 'read_only': True}
        try:
            symbol = str(symbol).upper().replace('/', '')
            raw = self.api.get_candles(symbol, int(interval), max(1, min(int(count), 3000)), time.time())
            out = [{'timestamp': c.get('from'), 'open': c.get('open'), 'high': c.get('max'), 'low': c.get('min'), 'close': c.get('close'), 'volume': c.get('volume', 0)} for c in raw or []]
            return {'ok': True, 'symbol': symbol, 'interval_seconds': int(interval), 'candles': out, 'source': 'IQ_OPTION_WEBSHARE', 'read_only': True}
        except Exception as exc:
            return {'ok': False, 'reason': f'IQ_OPTION_CANDLES_UNAVAILABLE:{type(exc).__name__}'}

    def payout(self, symbol):
        if not self.connected or not self.api: return {'ok': False, 'reason': _state.get('reason') or 'IQ_OPTION_CONNECTING', 'read_only': True}
        try:
            symbol = str(symbol).upper().replace('/', '')
            for name in ('get_digital_payout', 'get_binary_payout'):
                fn = getattr(self.api, name, None)
                if callable(fn): return {'ok': True, 'symbol': symbol, 'payout': fn(symbol), 'source': 'IQ_OPTION_WEBSHARE', 'read_only': True}
            return {'ok': False, 'reason': 'PAYOUT_NOT_EXPOSED_BY_SDK'}
        except Exception: return {'ok': False, 'reason': 'IQ_OPTION_PAYOUT_UNAVAILABLE'}

def connection_status():
    return dict(_state)
