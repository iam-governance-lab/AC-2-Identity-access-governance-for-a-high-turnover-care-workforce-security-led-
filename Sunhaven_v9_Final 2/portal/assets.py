"""Bounded static-file cache; never caches user data or authorization."""
from functools import lru_cache
from pathlib import Path
from hashlib import sha256
import gzip
@lru_cache(maxsize=24)
def cached_asset(path,mtime_ns,size,compressed=False):
    raw=Path(path).read_bytes()
    if compressed:raw=gzip.compress(raw,compresslevel=6,mtime=0)
    return raw,'"'+sha256(raw).hexdigest()+'"'

def accepts_gzip(header):
    for item in header.lower().split(','):
        parts=[x.strip() for x in item.split(';')]
        if parts[0]!='gzip':continue
        try:return all(float(x[2:])>0 for x in parts[1:] if x.startswith('q='))
        except ValueError:return False
    return False
