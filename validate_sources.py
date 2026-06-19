#!/usr/bin/env python3
# validate_sources.py - AVEC WHOIS DIRECT
import asyncio
import aiohttp
import json
from datetime import datetime, timezone
import whois  # <-- Nouvelle bibliothèque

# --- Configuration ---
AHREFS_URL = "https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}"
ARCHIVE_URL = "https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=100&fl=timestamp"

TIMEOUT_AHREFS = 5.0
TIMEOUT_ARCHIVE = 10.0
USER_AGENT = "DomainScorer-Validator/1.0"

TEST_DOMAINS = ["google.com", "openai.com", "shopify.com", "bitcoin.org", "random-domain-xyz-123.com"]

def get_whois_age(domain):
    """Récupère l'âge via whois library (direct, sans API externe)"""
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        if not creation_date:
            return None
        # Si c'est une liste, on prend la première date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - creation_date).days
        return max(0, days)
    except Exception as e:
        print(f"[WHOIS] {domain} -> ERREUR: {e}")
        return None

async def fetch_ahrefs(session, domain):
    try:
        url = AHREFS_URL.format(domain=domain)
        async with session.get(url, timeout=TIMEOUT_AHREFS) as resp:
            print(f"\n[AHREFS] {domain} -> status {resp.status}")
            if resp.status != 200:
                return None
            data = await resp.json()
            print(f"[AHREFS] {domain} -> DR: {data.get('domain_rating', {}).get('domain_rating')}")
            dr = data.get("domain_rating", {}).get("domain_rating")
            return float(dr) if dr is not None else None
    except Exception as e:
        print(f"[AHREFS] {domain} -> ERREUR: {e}")
        return None

async def fetch_archive(session, domain):
    try:
        url = ARCHIVE_URL.format(domain=domain)
        async with session.get(url, timeout=TIMEOUT_ARCHIVE) as resp:
            print(f"\n[ARCHIVE] {domain} -> status {resp.status}")
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data or len(data) < 2:
                return None
            return len(data) - 1
    except asyncio.TimeoutError:
        print(f"[ARCHIVE] {domain} -> TIMEOUT")
        return None
    except Exception as e:
        print(f"[ARCHIVE] {domain} -> ERREUR: {e}")
        return None

async def main():
    print("\n🚀 VALIDATION FINALE (avec whois direct)\n")
    async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
        results = []
        for domain in TEST_DOMAINS:
            print(f"\n{'='*60}")
            print(f"🔍 ANALYSE DE {domain}")
            print('='*60)
            # WHOIS en synchrone (rapide)
            age = get_whois_age(domain)
            print(f"[WHOIS] {domain} -> Âge: {age} jours")
            # Ahrefs et Archive en parallèle
            ahrefs, archive = await asyncio.gather(
                fetch_ahrefs(session, domain),
                fetch_archive(session, domain)
            )
            results.append({
                "domain": domain,
                "whois_age_days": age,
                "ahrefs_dr": ahrefs,
                "archive_snapshot_count": archive
            })
            print(f"\n✅ RÉSULTAT {domain}:")
            print(f"   Âge: {age} jours")
            print(f"   DR: {ahrefs}")
            print(f"   Snapshots: {archive}")

    print("\n📊 SYNTHÈSE FINALE :\n")
    print("-" * 70)
    print(f"{'Domaine':<30} {'Âge (jours)':<14} {'DR':<8} {'Snapshots':<10}")
    print("-" * 70)
    for r in results:
        age = r["whois_age_days"] if r["whois_age_days"] is not None else "❌"
        dr = r["ahrefs_dr"] if r["ahrefs_dr"] is not None else "❌"
        arch = r["archive_snapshot_count"] if r["archive_snapshot_count"] is not None else "❌"
        print(f"{r['domain']:<30} {str(age):<14} {str(dr):<8} {str(arch):<10}")
    print("-" * 70)

if __name__ == "__main__":
    asyncio.run(main())