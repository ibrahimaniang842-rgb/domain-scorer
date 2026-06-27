# src/fetchers/wayback_content_fetcher.py
import aiohttp
import asyncio
from typing import Optional, List, Dict

async def get_wayback_snapshots(domain: str, session: aiohttp.ClientSession) -> List[Dict]:
    """
    Récupère 3 snapshots significatifs : ancien, milieu, récent.
    Retourne une liste de dict avec 'timestamp' et 'html'.
    """
    # 1. Récupérer la liste des timestamps
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=100&fl=timestamp"
    try:
        async with session.get(cdx_url, timeout=5.0) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            if not data or len(data) < 2:
                return []
            # Extraire les timestamps (colonnes)
            timestamps = [row[0] for row in data[1:]]  # data[0] est l'en-tête
            if not timestamps:
                return []
            # Sélectionner 3 snapshots : premier, milieu, dernier
            selected = []
            if len(timestamps) >= 3:
                selected = [timestamps[0], timestamps[len(timestamps)//2], timestamps[-1]]
            elif len(timestamps) == 2:
                selected = [timestamps[0], timestamps[-1]]
            else:
                selected = [timestamps[0]]

            # 2. Récupérer le HTML pour chaque timestamp
            results = []
            for ts in selected:
                html = await _fetch_snapshot_html(domain, ts, session)
                results.append({
                    "timestamp": ts,
                    "html": html
                })
            return results
    except Exception:
        return []

async def _fetch_snapshot_html(domain: str, timestamp: str, session: aiohttp.ClientSession) -> Optional[str]:
    url = f"https://web.archive.org/web/{timestamp}id_/{domain}"
    try:
        async with session.get(url, timeout=5.0) as resp:
            if resp.status == 200:
                return await resp.text()
            return None
    except Exception:
        return None