import os, re
from http.server import SimpleHTTPRequestHandler
class RangeHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        m = re.match(r'bytes=(\d*)-(\d*)', rng)
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        f = open(path, 'rb'); f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        self._remaining = end - start + 1
        return f
    def copyfile(self, source, outputfile):
        n = getattr(self, '_remaining', None)
        if n is None: return super().copyfile(source, outputfile)
        while n > 0:
            buf = source.read(min(65536, n))
            if not buf: break
            outputfile.write(buf); n -= len(buf)
        self._remaining = None
