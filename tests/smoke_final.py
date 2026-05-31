"""Quick smoke: TED + Bund connector URL validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_smoke_final.db")
import requests

def chk(url):
    if not url:
        return "EMPTY"
    try:
        r = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return f"HTTP {r.status_code}"
    except Exception as e:
        return f"ERR"

print("=== TED ===")
from connectors.ted import TEDConnector
tc = TEDConnector()
ts = tc.fetch_recent(days_back=30)
print(f"TED tenders: {len(ts)}")
for t in ts[:5]:
    status = chk(t["url"])
    print(f"  {status}  {t['url']}")

print()
print("=== BUND ===")
from connectors.bund import BundConnector
bc = BundConnector(max_pages=1)
bs = bc.fetch_recent(days_back=30)
print(f"BUND tenders: {len(bs)}")
for t in bs[:5]:
    status = chk(t["url"])
    print(f"  {status}  {t['url']}")
