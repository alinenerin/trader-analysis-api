"""Persistent, non-blocking IQ Option read-only session through current Webshare proxy."""
import os, time, threading

_client = None
_state = {'status': 'starting', 'reason': None, 'connected_at': None}
_lock = threading.RLock()
_start_once = False

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
                self.api = _client.api
                self.connected = bool(self.api)
            if not _start_once:
                _start_once = True
                threading.Thread(target=self._connect_worker, daemon=True, name='iqoption-session').start()

    def _connect_worker(self):
        global _client, _state
        with _lock:
            if self.api and self.connected:
                return
            if not self.email or not self.password:
                _state.update(status='error', reason='IQ_OPTION_CREDENTIALS_NOT_CONFIGURED'); return
            _state.update(status='connecting', reason=None)
        try:
            from iqoptionapi.stable_api import IQ_Option
            # SDK websocket uses these kwargs in run_forever; this avoids global monkeypatches.
            import websocket
            host = os.getenv('WEBSHARE_SOCKS_HOST', '31.59.20.176')
            port = int(os.getenv('WEBSHARE_SOCKS_PORT', '6754'))
            user = os.getenv('WEBSHARE_SOCKS_USERNAME', '')
            pwd = os.getenv('WEBSHARE_SOCKS_PASSWORD', '')
            original = websocket.WebSocketApp.run_forever
            def proxied(ws, *args, **kwargs):
                kwargs.setdefault('http_proxy_host', host)
                kwargs.setdefault('http_proxy_port', port)
                kwargs.setdefault('proxy_type', 'http')
                if user: kwargs.setdefault('http_proxy_auth', (user, pwd))
                return original(ws, *args, **kwargs)
            websocket.WebSocketApp.run_forever = proxied
            api = IQ_Option(self.email, self.password)
            ok, reason = api.connect()
            if not ok:
                _state.update(status='error', reason=str(reason or 'IQ_OPTION_LOGIN_FAILED')[:180]); return
            api.change_balance(self.balance_mode)
            with _lock:
                self.api = api; self.connected = True; _client = self
                _state.update(status='connected', reason=None, connected_at=time.time())
        except Exception as exc:
            _state.update(status='error', reason=f'{type(exc).__name__}: {exc}'[:180])

    def connect(self):
        # Never block an HTTP request on the IQ websocket.
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
