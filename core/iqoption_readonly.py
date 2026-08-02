"""Read-only IQ Option market-data adapter using the legacy working connection path."""
import os, time

class IQOptionReadonly:
    def __init__(self):
        self.email = os.getenv('IQ_OPTION_EMAIL') or os.getenv('IQ_USER', '')
        self.password = os.getenv('IQ_OPTION_PASSWORD') or os.getenv('IQ_PASS', '')
        self.balance_mode = os.getenv('IQ_OPTION_BALANCE_MODE') or os.getenv('BALANCE_MODE', 'PRACTICE')
        self.connected = False
        self.api = None

    def connect(self):
        if not self.email or not self.password:
            return False, 'IQ_OPTION_CREDENTIALS_NOT_CONFIGURED'
        try:
            # The legacy production workflow did NOT set a proxy: it connected
            # directly from its runner. Keep direct mode as the default and only
            # enable Webshare when explicitly requested.
            use_proxy = os.getenv('IQ_OPTION_USE_PROXY', 'true').lower() == 'true'
            if use_proxy:
                socks_host = os.getenv('WEBSHARE_SOCKS_HOST', 'socks.webshare.io')
                socks_port = os.getenv('WEBSHARE_SOCKS_PORT', '1080')
                socks_user = os.getenv('WEBSHARE_SOCKS_USERNAME', '')
                socks_pass = os.getenv('WEBSHARE_SOCKS_PASSWORD', '')
                proxy_url = f'socks5h://{socks_user}:{socks_pass}@{socks_host}:{socks_port}'
                os.environ['ALL_PROXY'] = proxy_url
                os.environ['all_proxy'] = proxy_url
            else:
                # Do not inherit stale proxy variables from the container.
                for key in ('ALL_PROXY','all_proxy','HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):
                    os.environ.pop(key, None)
            from iqoptionapi.stable_api import IQ_Option
            self.api = IQ_Option(self.email, self.password)
            import signal
            class _ConnectTimeout(Exception): pass
            def _alarm(_signum, _frame): raise _ConnectTimeout()
            previous_handler = signal.signal(signal.SIGALRM, _alarm)
            signal.alarm(int(os.getenv('IQ_OPTION_CONNECT_TIMEOUT', '25')))
            try:
                ok, reason = self.api.connect()
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous_handler)
            if not ok:
                print(f'IQ Option legacy connection rejected: {str(reason)[:120]}')
                return False, f'IQ_OPTION_CONNECTION_FAILED:{str(reason or "UNKNOWN")[:120]}'
            self.api.change_balance(self.balance_mode)
            self.connected = True
            return True, 'CONNECTED_READ_ONLY'
        except ImportError:
            return False, 'IQ_OPTION_SDK_IMPORT_FAILED'
        except Exception as exc:
            print(f'IQ Option legacy connection failed: {type(exc).__name__}: {exc}')
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
