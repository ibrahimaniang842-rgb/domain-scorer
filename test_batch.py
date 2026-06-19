# test_batch.py
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/score"
FICHIER_DOMAINES = "domaines.txt"
FICHIER_RESULTATS = f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def lire_domaines(fichier):
    with open(fichier, 'r') as f:
        return [ligne.strip() for ligne in f if ligne.strip()]

def analyser_domaine(domaine):
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}?domain={domaine}", timeout=20)
        elapsed = round(time.time() - start, 2)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "domaine": domaine,
                "status": "OK",
                "seo_score": data.get("seo_score"),
                "monetization_score": data.get("monetization_score"),
                "danger_level": data.get("danger_level"),
                "danger_reasons": data.get("danger_reasons", []),
                "raw": data.get("raw_data", {}),
                "temps": elapsed
            }
        else:
            return {
                "domaine": domaine,
                "status": f"Erreur {resp.status_code}",
                "seo_score": None,
                "monetization_score": None,
                "danger_level": None,
                "danger_reasons": [],
                "raw": {},
                "temps": elapsed
            }
    except Exception as e:
        return {
            "domaine": domaine,
            "status": f"Exception: {str(e)[:60]}",
            "seo_score": None,
            "monetization_score": None,
            "danger_level": None,
            "danger_reasons": [],
            "raw": {},
            "temps": 0
        }

def main():
    print("\n🚀 TEST BATCH : ANALYSE DE DOMAINES")
    print("=" * 70)
    
    domaines = lire_domaines(FICHIER_DOMAINES)
    print(f"📋 {len(domaines)} domaines chargés depuis {FICHIER_DOMAINES}\n")
    
    resultats = []
    for i, domaine in enumerate(domaines, 1):
        print(f"[{i}/{len(domaines)}] Analyse de {domaine}...", end=" ", flush=True)
        resultat = analyser_domaine(domaine)
        resultats.append(resultat)
        print(f"SEO: {resultat['seo_score']} | Danger: {resultat['danger_level']} | {resultat['temps']}s")
        
        # Pause courte pour ne pas surcharger l'API
        time.sleep(1)
    
    # Sauvegarde des résultats
    with open(FICHIER_RESULTATS, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    
    # Affichage tableau
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS COMPLETS")
    print("=" * 70)
    print(f"{'Domaine':<30} {'SEO':<8} {'Mono':<8} {'Danger':<8} {'Temps':<6} {'Statut'}")
    print("-" * 70)
    
    for r in resultats:
        seo = str(r['seo_score']) if r['seo_score'] is not None else "---"
        mono = str(r['monetization_score']) if r['monetization_score'] is not None else "---"
        danger = r['danger_level'] if r['danger_level'] else "---"
        print(f"{r['domaine']:<30} {seo:<8} {mono:<8} {danger:<8} {r['temps']:<6}s {r['status']}")
    
    print("-" * 70)
    
    # Statistiques
    ok_count = sum(1 for r in resultats if r['status'] == 'OK')
    print(f"\n✅ {ok_count}/{len(domaines)} domaines analysés avec succès.")
    print(f"📁 Résultats sauvegardés dans {FICHIER_RESULTATS}")
    
    # Top 5 SEO
    valides = [r for r in resultats if r['seo_score'] is not None]
    top5 = sorted(valides, key=lambda x: x['seo_score'], reverse=True)[:5]
    if top5:
        print("\n🏆 TOP 5 SEO :")
        for i, r in enumerate(top5, 1):
            print(f"  {i}. {r['domaine']} → SEO: {r['seo_score']} | Danger: {r['danger_level']}")

if __name__ == "__main__":
    main()