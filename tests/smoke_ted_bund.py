"""Smoke test TED and Bund connectors."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_smoke2.db")
import requests

def chk(url):
    if not url:
        return "EMPTY"
    try:
        r = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return f"HTTP {r.status_code}"
    except Exception:
        return "ERR"

print("=== TED ===")
from connectors.ted import TEDConnector
tc = TEDConnector()
ts = tc.fetch_recent(days_back=30)
print(f"Tenders: {len(ts)}")
for t in ts[:3]:
    url = t["url"]
    print(f"  {chk(url)}  {url[:70]}")
    print(f"    {t['title'][:60]}")

print()
print("=== BUND ===")
from connectors.bund import BundConnector
bc = BundConnector(max_pages=1)
bs = bc.fetch_recent(days_back=30)
print(f"Tenders: {len(bs)}")
for t in bs[:3]:
    url = t["url"]
    print(f"  {chk(url)}  {url[:70]}")
    print(f"    {t['title'][:60]}")
