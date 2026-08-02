from pathlib import Path
import websocket
p = Path(websocket.__file__).with_name('_app.py')
s = p.read_text()
start = s.find('    def _callback(self, callback, *args):')
if start < 0:
    raise SystemExit('callback method not found')
end = s.find('\n    def ', start + 10)
if end < 0:
    raise SystemExit('next method not found')
new = '''    def _callback(self, callback, *args):
        # Prevent the legacy client from recursively re-entering its callback
        # dispatcher when the handshake/error callback itself raises.
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
p.write_text(s[:start] + new + s[end:])
print(p)
