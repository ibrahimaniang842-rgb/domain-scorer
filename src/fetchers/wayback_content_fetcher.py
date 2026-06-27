# src/fetchers/wayback_content_fetcher.py
import aiohttp
import asyncio
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

async def get_wayback_snapshots(domain: str, session: aiohttp.ClientSession) -> List[Dict]:
    """
    Récupère jusqu'à 5 snapshots significatifs : ancien, milieu, récent.
    Retourne une liste de dict avec 'timestamp' et 'html'.
    """
    # 1. Récupérer la liste des timestamps
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=200&fl=timestamp"
    try:
        logger.info(f"[WAYBACK] Récupération des snapshots pour {domain}")
        async with session.get(cdx_url, timeout=8.0) as resp:
            if resp.status != 200:
                logger.warning(f"[WAYBACK] {domain} -> HTTP {resp.status}")
                return []
            data = await resp.json()
            if not data or len(data) < 2:
                logger.info(f"[WAYBACK] {domain} -> Aucun snapshot trouvé")
                return []
            # Extraire les timestamps
            timestamps = [row[0] for row in data[1:]]
            if not timestamps:
                return []
            # Sélectionner jusqu'à 5 snapshots bien répartis
            selected = []
            n = len(timestamps)
            if n >= 5:
                indices = [0, n//4, n//2, 3*n//4, n-1]
            elif n >= 3:
                indices = [0, n//2, n-1]
            else:
                indices = list(range(n))
            selected = [timestamps[i] for i in indices if i < n]
            logger.info(f"[WAYBACK] {domain} -> {len(selected)} snapshots sélectionnés")

            # 2. Récupérer le HTML pour chaque timestamp
            results = []
            for ts in selected:
                html = await _fetch_snapshot_html(domain, ts, session)
                if html and len(html) > 500:  # Ignorer les pages trop petites
                    results.append({
                        "timestamp": ts,
                        "html": html
                    })
                else:
                    logger.info(f"[WAYBACK] {domain} -> Snapshot {ts} trop petit ou vide")
            logger.info(f"[WAYBACK] {domain} -> {len(results)} snapshots récupérés avec succès")
            return results
    except asyncio.TimeoutError:
        logger.warning(f"[WAYBACK] {domain} -> TIMEOUT")
        return []
    except Exception as e:
        logger.warning(f"[WAYBACK] {domain} -> ERREUR: {e}")
        return []

async def _fetch_snapshot_html(domain: str, timestamp: str, session: aiohttp.ClientSession) -> Optional[str]:
    url = f"https://web.archive.org/web/{timestamp}id_/{domain}"
    try:
        async with session.get(url, timeout=8.0) as resp:
            if resp.status == 200:
                return await resp.text()
            return None
    except Exception:
        return None