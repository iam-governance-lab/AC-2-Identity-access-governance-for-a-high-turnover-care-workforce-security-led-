"""Single UTC business clock for contract, qualification and review boundaries."""
from datetime import datetime, timezone

def utc_today():
    return datetime.now(timezone.utc).date()
