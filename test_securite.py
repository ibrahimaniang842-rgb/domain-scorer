# test_securite.py
import requests

ENTREES = [
    ("test", 400),
    ("https://google.com", 200),
    ("www.google.com", 200),
    ("google..com", 400),
    ("-google.com", 400),
    ("google.com/", 400),
    ("", 400)
]

print("🔒 TEST DE SÉCURITÉ")
print("=" * 60)

for entree, expected in ENTREES:
    resp = requests.get(f"http://localhost:8000/score?domain={entree}")
    status = resp.status_code
    ok = "✅" if status == expected else "❌"
    print(f"  {ok} '{entree}' → {status} (attendu: {expected})")