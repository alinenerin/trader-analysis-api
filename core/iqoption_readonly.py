"""Persistent read-only IQ Option session via Webshare SOCKS5."""
import os, time, threading

_client = None
_state = {'status': 'starting', 'reason': None, 'connected_at': None}
_lock = threading.Lock()

class IQOptionReadonly:
    def __init__(self):
        self.email = os.getenv('IQ_OPTION_EMAIL') or os.getenv('IQ_USER', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD') or os.getenv('IQ_PASS', '')
        self.balance_mode = os.getenv('IQ_OPTION_BALANCE_MODE') or os.getenv('BALANCE_MODE', 'PRACTICE')
        self.connected = False
        self.api = None

    def connect(self):
        global _client, _state
        with _lock:
            if self.connected and self.api:
                return True, 'CONNECTED_READ_ONLY'
            if not self.email or not self.password:
                _state.update(status='error', reason='IQ_OPTION_CREDENTIALS_NOT_CONFIGURED')
                return False, _state['reason']
            try:
                # Webshare is the required route; configure it before SDK creation.
                host = os.getenv('WEBSHARE_SOCKS_HOST', 'socks.webshare.io')
                port = int(os.getenv('WEBSHARE_SOCKS_PORT', '1080'))
                user = os.getenv('WEBSHARE_SOCKS_USERNAME', '')
                pwd = os.getenv('WEBSHARE_SOCKS_PASSWORD', '')
                import websocket
                from iqoptionapi.stable_api import IQ_Option
                proxy_kwargs = {'http_proxy_host': host, 'http_proxy_port': port,
                                'proxy_type': 'socks5h'}
                if user: proxy_kwargs['http_proxy_auth'] = (user, pwd)
                original = websocket.WebSocketApp.run_forever
                def run_forever(ws, *args, **kwargs):
                    kwargs.update(proxy_kwargs)
                    return original(ws, *args, **kwargs)
                websocket.WebSocketApp.run_forever = run_forever
                self.api = IQ_Option(self.email, self.password)
                _state['status'] = 'connecting'
                ok, reason = self.api.connect()
                if not ok:
                    _state.update(status='error', reason=str(reason or 'IQ_OPTION_LOGIN_FAILED')[:180])
                    return False, _state['reason']
                self.api.change_balance(self.balance_mode)
                self.connected = True
                _client = self
                _state.update(status='connected', reason=None, connected_at=time.time())
                return True, 'CONNECTED_READ_ONLY'
            except Exception as exc:
                _state.update(status='error', reason=f'{type(exc).__name__}: {exc}'[:180])
                return False, _state['reason']

    def candles(self, symbol, interval=60, count=1000):
        if not self.connected:
            ok, reason = self.connect()
            if not ok: return {'ok': False, 'reason': reason}
        try:
            symbol = str(symbol).upper().replace('/', '')
            raw = self.api.get_candles(symbol, int(interval), max(1, min(int(count), 3000)), time.time())
            out = [{'timestamp': c.get('from'), 'open': c.get('open'), 'high': c.get('max'),
                    'low': c.get('min'), 'close': c.get('close'), 'volume': c.get('volume', 0)} for c in raw or []]
            return {'ok': True, 'symbol': symbol, 'interval_seconds': int(interval), 'candles': out,
                    'source': 'IQ_OPTION_WEBSHARE', 'read_only': True}
        except Exception as exc:
            return {'ok': False, 'reason': f'IQ_OPTION_CANDLES_UNAVAILABLE:{type(exc).__name__}'}

    def payout(self, symbol):
        if not self.connected:
            ok, reason = self.connect()
            if not ok: return {'ok': False, 'reason': reason}
        try:
            symbol = str(symbol).upper().replace('/', '')
            for name in ('get_digital_payout', 'get_binary_payout'):
                fn = getattr(self.api, name, None)
                if callable(fn):
                    v = fn(symbol); return {'ok': v is not None, 'symbol': symbol, 'payout': v, 'source': 'IQ_OPTION_WEBSHARE', 'read_only': True}
            return {'ok': False, 'reason': 'PAYOUT_NOT_EXPOSED_BY_SDK'}
        except Exception: return {'ok': False, 'reason': 'IQ_OPTION_PAYOUT_UNAVAILABLE'}

def connection_status():
    return dict(_state)
