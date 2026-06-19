import requests
import json

print("🔍 Test healthcheck...")
resp = requests.get("http://localhost:8000/health")
print(resp.json())

print("\n🔍 Test score pour openai.com...")
resp = requests.get("http://localhost:8000/score?domain=openai.com")
if resp.status_code == 200:
    data = resp.json()
    print(json.dumps(data, indent=2))
else:
    print(f"Erreur {resp.status_code}: {resp.text}")

print("\n🔍 Test domaine invalide...")
resp = requests.get("http://localhost:8000/score?domain=test")
print(f"Statut: {resp.status_code}")
print(resp.text)