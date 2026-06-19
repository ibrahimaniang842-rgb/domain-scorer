# test_coherence.py
import requests
import json

DOMAINES = ["google.com", "shopify.com", "openai.com", "bitcoin.org", "test12345.com"]
BASE_URL = "http://localhost:8000/score"

print("🧠 TEST DE COHÉRENCE DES SCORES")
print("=" * 60)

scores = {}
for domaine in DOMAINES:
    resp = requests.get(f"{BASE_URL}?domain={domaine}")
    if resp.status_code == 200:
        data = resp.json()
        scores[domaine] = data.get("seo_score")
        print(f"  {domaine}: {scores[domaine]}")
    else:
        print(f"  {domaine}: ❌ Erreur {resp.status_code}")

# Vérification de l'ordre
ordre = sorted(scores.items(), key=lambda x: x[1], reverse=True)
print("\n📊 Classement SEO :")
for i, (domaine, score) in enumerate(ordre, 1):
    print(f"  {i}. {domaine}: {score}")

print("\n✅ Vérification : google.com doit être en tête, test12345.com en queue.")