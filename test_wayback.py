# test_wayback.py
import asyncio
import aiohttp
import json
from src.fetchers.wayback_content_fetcher import get_wayback_snapshots

async def test_domain(domain: str):
    print(f"\n🔍 Test de {domain}")
    async with aiohttp.ClientSession() as session:
        result = await get_wayback_snapshots(domain, session)
        print(f"Statut  : {result['status']}")
        print(f"Snapshots disponibles : {result['total_available']}")
        print(f"Années couvertes : {result['years_covered']}")
        print(f"Nombre de snapshots récupérés : {len(result['snapshots'])}")
        for s in result['snapshots']:
            print(f"  - {s['year']} : {len(s['text'])} caractères (extrait: {s['text'][:100]}...)")

async def main():
    # Test sur plusieurs domaines
    domains = [
        "google.com",
        "openai.com",
        "toysrus.com",
        "lemonde.fr"
    ]
    for domain in domains:
        await test_domain(domain)

if __name__ == "__main__":
    asyncio.run(main())