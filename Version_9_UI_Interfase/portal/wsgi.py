"""WSGI adapter retaining the tested route handlers; served by Waitress in deployment.

The stdlib HTTP server remains available for a dependency-free local demo. This
adapter replaces its HTTP parsing/transport, not the business logic.
"""
from email.message import Message
from http import HTTPStatus
from io import BytesIO
import config
from server import AppHandler

class WSGIHandler(AppHandler):
    def __init__(self, environ):
        self.headers = Message()
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                self.headers[key[5:].replace('_','-')] = value
        for key in ('CONTENT_LENGTH','CONTENT_TYPE'):
            if environ.get(key):
                self.headers[key.replace('_','-')] = environ[key]
        self.command = environ['REQUEST_METHOD']
        self.path = environ.get('PATH_INFO','/') + ('?' + environ['QUERY_STRING'] if environ.get('QUERY_STRING') else '')
        self.client_address = (environ.get('REMOTE_ADDR',''), 0)
        self.rfile = environ['wsgi.input']
        self.wfile = BytesIO()
        self.status_code = 200
        self.response_headers = []

    def send_response(self, code, message=None):
        self.status_code = code

    def send_header(self, keyword, value):
        if keyword.lower() == 'set-cookie' and config.SECURE_COOKIES and '; Secure' not in value:
            value += '; Secure'
        self.response_headers.append((keyword,str(value)))

    def end_headers(self):
        if config.SECURE_COOKIES:self.send_header("Strict-Transport-Security","max-age=31536000")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Request-ID",getattr(self,"request_id",""))
        self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=()")

    def log_message(self, fmt, *args):
        pass

def application(environ, start_response):
    handler = WSGIHandler(environ)
    if handler.command not in ('GET','POST'):
        handler.send_response(405)
        handler.send_header('Allow','GET, POST')
        handler.send_header('Content-Type','text/plain')
        handler.wfile.write(b'Method not allowed')
    else:
        handler._dispatch(handler.command)
    headers = handler.response_headers
    if not any(k.lower() == 'cache-control' for k,v in headers):
        headers.append(('Cache-Control','no-store'))
    if config.SECURE_COOKIES:
        headers.append(('Strict-Transport-Security','max-age=31536000'))
    body = handler.wfile.getvalue()
    if not any(k.lower() == 'content-length' for k,v in headers):
        headers.append(('Content-Length',str(len(body))))
    start_response(f'{handler.status_code} {HTTPStatus(handler.status_code).phrase}',headers)
    return [body]
