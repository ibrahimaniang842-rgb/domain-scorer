import asyncio
import whois
from datetime import datetime, timezone
from typing import Optional

def _sync_whois(domain: str) -> Optional[int]:
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        if not creation_date:
            return None
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - creation_date).days
        return max(0, days)
    except Exception:
        return None

async def get_whois_age(domain: str) -> Optional[int]:
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _sync_whois, domain),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        return None