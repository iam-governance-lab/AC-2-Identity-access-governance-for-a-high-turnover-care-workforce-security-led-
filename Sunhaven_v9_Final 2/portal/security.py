"""Signed double-submit CSRF tokens; all state-changing forms are protected."""
import hashlib
import hmac
import secrets
import auth
import config

_KEY = (config.SECRET_KEY or secrets.token_hex(32)).encode()

def signed(nonce):
    return nonce + '.' + hmac.new(_KEY, nonce.encode(), hashlib.sha256).hexdigest()

def valid(value):
    if not value or len(value) > 200 or '.' not in value:
        return False
    nonce, _ = value.rsplit('.', 1)
    return hmac.compare_digest(signed(nonce), value)

def token(handler):
    old = auth.parse_cookies(handler).get('sunhaven_csrf')
    return old.value if old and valid(old.value) else signed(secrets.token_hex(24))

def validate(handler, submitted):
    old = auth.parse_cookies(handler).get('sunhaven_csrf')
    return bool(old and valid(submitted) and hmac.compare_digest(old.value, submitted))

def cookie(value):
    return f'sunhaven_csrf={value}; Path=/; HttpOnly; SameSite=Strict' + ('; Secure' if config.SECURE_COOKIES else '')


def rate_allowed(address,category):
    """Transactional per-client fixed window. Reverse proxies need their own edge limits."""
    import time, database
    window=int(time.time())//60;limit=30 if category in ('login','assistant') else 120
    key=hashlib.sha256((str(address)+':'+category+':'+str(window)).encode()).hexdigest()
    with database.connect(integrity=False) as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM http_rate_limits WHERE expires_at<?',(int(time.time()),))
        c.execute('INSERT INTO http_rate_limits VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=hits+1',(key,(window+1)*60))
        return c.execute('SELECT hits FROM http_rate_limits WHERE bucket=?',(key,)).fetchone()[0]<=limit
