from pathlib import Path
import websocket
p = Path(websocket.__file__).with_name('_app.py')
s = p.read_text()
old = '''    def _callback(self, callback, *args):
        if callback:
            try:
                if inspect.ismethod(callback):
                    callback(*args)
                else:
                    callback(self, *args)
            except Exception as e:
                _logging.error("error from callback {}: {}".format(callback, e))
                if _logging.isEnabledForDebug():
                    _, _, tb = sys.exc_info()
                    traceback.print_tb(tb)
'''
new = '''    def _callback(self, callback, *args):
        # The legacy client can re-enter _callback on malformed handshake errors.
        # Never recurse; surface the original callback failure to the caller/log.
        if not callback or callback is self._callback:
            return
        try:
            if inspect.ismethod(callback):
                callback(*args)
            else:
                callback(self, *args)
        except Exception as e:
            _logging.error("websocket callback failed: %s", e, exc_info=True)
            self.keep_running = False
'''
if old not in s:
    raise SystemExit(f'expected callback block not found in {p}')
p.write_text(s.replace(old, new))
print(p)
