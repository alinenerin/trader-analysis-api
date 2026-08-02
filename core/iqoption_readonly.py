"""IQ Option market-data adapter. Read-only by design: no buy/sell methods are exposed."""
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
        # The proxy is applied before the SDK opens HTTP/WebSocket connections.
        host, port = os.getenv('WEBSHARE_HOST', ''), os.getenv('WEBSHARE_PORT', '')
        user, pwd = os.getenv('WEBSHARE_USERNAME', ''), os.getenv('WEBSHARE_PASSWORD', '')
        if host and port:
            proxy = f'http://{user}:{pwd}@{host}:{port}' if user and pwd else f'http://{host}:{port}'
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy
            os.environ['http_proxy'] = proxy
            os.environ['https_proxy'] = proxy
        try:
            from iqoptionapi.stable_api import IQ_Option
            self.api = IQ_Option(self.email, self.password)
            ok, reason = self.api.connect()
            if not ok:
                return False, 'IQ_OPTION_CONNECTION_FAILED'
            self.api.change_balance(self.balance_mode)
            self.connected = True
            return True, 'CONNECTED_READ_ONLY'
        except ImportError:
            return False, 'IQ_OPTION_SDK_NOT_INSTALLED'
        except Exception:
            return False, 'IQ_OPTION_CONNECTION_ERROR'

    def candles(self, symbol, interval=60, count=1000):
        if not self.connected:
            ok, reason = self.connect()
            if not ok: return {'ok': False, 'reason': reason}
        symbol = str(symbol).upper().replace('/', '')
        count = max(1, min(int(count), 3000))
        interval = int(interval)
        try:
            raw = self.api.get_candles(symbol, interval, count, time.time())
            candles = []
            for c in raw or []:
                candles.append({'timestamp': c.get('from'), 'open': c.get('open'), 'high': c.get('max'),
                                'low': c.get('min'), 'close': c.get('close'), 'volume': c.get('volume', 0)})
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
            # Different SDK versions expose different payout methods; never infer a value.
            value = None
            for name in ('get_digital_payout', 'get_binary_payout'):
                fn = getattr(self.api, name, None)
                if callable(fn):
                    value = fn(symbol); break
            return {'ok': value is not None, 'symbol': symbol, 'payout': value,
                    'source': 'IQ_OPTION', 'read_only': True,
                    'reason': None if value is not None else 'PAYOUT_NOT_EXPOSED_BY_SDK'}
        except Exception:
            return {'ok': False, 'reason': 'IQ_OPTION_PAYOUT_UNAVAILABLE', 'symbol': symbol}
