# test_fetchers.py - Diagnostic des fetchers
import asyncio
import aiohttp
from src.fetchers.whois_fetcher import get_whois_age
from src.fetchers.ahrefs_fetcher import get_ahrefs_dr
from src.fetchers.archive_fetcher import get_archive_snapshot_count

async def test_all(domain):
    async with aiohttp.ClientSession() as session:
        print(f"\n🔍 TEST POUR {domain}\n")
        
        # WHOIS
        print("1. WHOIS...")
        age = await get_whois_age(domain)
        print(f"   Âge: {age}\n")
        
        # Ahrefs
        print("2. Ahrefs DR...")
        dr = await get_ahrefs_dr(domain, session)
        print(f"   DR: {dr}\n")
        
        # Archive
        print("3. Archive...")
        archive = await get_archive_snapshot_count(domain, session)
        print(f"   Snapshots: {archive}\n")

if __name__ == "__main__":
    asyncio.run(test_all("openai.com"))