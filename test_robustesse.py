# test_robustesse.py
import requests
import json
import time

DOMAINES = [
    "google.com",
    "facebook.com",
    "amazon.com",
    "shopify.com",
    "bitcoin.org",
    "openai.com",
    "test12345.com",
    "un-domaine-inexistant-xyz-2026.com",
    "microsoft.com",
    "netflix.com"
]

BASE_URL = "http://localhost:8000/score"

print("🧪 TEST DE ROBUSTESSE DU SYSTÈME")
print("=" * 60)

resultats = []
for domaine in DOMAINES:
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}?domain={domaine}", timeout=30)
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            statut = "✅ OK"
            seo = data.get("seo_score")
            danger = data.get("danger_level")
            raw = data.get("raw_data", {})
            nb_donnees = sum(1 for v in raw.values() if v is not None)
        else:
            statut = f"❌ Erreur {resp.status_code}"
            seo = None
            danger = None
            nb_donnees = 0
    except Exception as e:
        statut = f"💥 Exception: {str(e)[:50]}"
        seo = None
        danger = None
        nb_donnees = 0
        elapsed = 0

    resultats.append({
        "domaine": domaine,
        "statut": statut,
        "seo": seo,
        "danger": danger,
        "nb_donnees": nb_donnees,
        "temps": round(elapsed, 2)
    })

# Affichage
print("\n📊 RÉSULTATS :")
print("-" * 80)
print(f"{'Domaine':<35} {'SEO':<8} {'Danger':<8} {'Données':<8} {'Temps':<6} {'Statut'}")
print("-" * 80)

for r in resultats:
    seo = str(r["seo"]) if r["seo"] is not None else "---"
    danger = r["danger"] if r["danger"] else "---"
    donnees = r["nb_donnees"]
    print(f"{r['domaine']:<35} {seo:<8} {danger:<8} {donnees:<8} {r['temps']:<6}s {r['statut']}")

print("-" * 80)

# Bilan
ok_count = sum(1 for r in resultats if r["statut"] == "✅ OK")
print(f"\n✅ {ok_count}/{len(DOMAINES)} domaines traités avec succès.")
print("\n👉 Un système robuste doit avoir au moins 90% de succès (9/10).")