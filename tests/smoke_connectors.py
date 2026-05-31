"""Quick smoke test — fetch 2-3 records from each connector and verify URLs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DATABASE_URL", "sqlite:///test_smoke.db")

import requests

def check_url(url: str) -> str:
    if not url:
        return "EMPTY"
    try:
        r = requests.head(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        return f"HTTP {r.status_code}"
    except Exception as e:
        return f"ERR: {type(e).__name__}"

# ── BMFTR ──────────────────────────────────────────────────────────────────
print("=== BMFTR ===")
from connectors.bmftr import BMFTRConnector, BMFTR_YEAR_URLS, BMFTR_BASE, _CALL_PAGE_RE
c = BMFTRConnector(delay=0.5, max_per_year=3)
links = c._collect_call_links(BMFTR_YEAR_URLS[0])
print(f"  Links from 2026 page: {len(links)}")
for link in links[:3]:
    status = check_url(link)
    print(f"  {status}  {link}")

# ── GBA ────────────────────────────────────────────────────────────────────
print("\n=== GBA ===")
from connectors.gba import GBAConnector
gc = GBAConnector(delay=0.5)
tenders = gc.fetch_recent()
print(f"  Tenders: {len(tenders)}")
for t in tenders[:3]:
    status = check_url(t["url"])
    print(f"  {status}  {t['url'][:80]}")
    print(f"    title: {t['title'][:60]}")

# ── TED ────────────────────────────────────────────────────────────────────
print("\n=== TED ===")
from connectors.ted import TEDConnector
tc = TEDConnector()
tenders_ted = tc.fetch_recent(days_back=30)
print(f"  Tenders: {len(tenders_ted)}")
for t in tenders_ted[:3]:
    status = check_url(t["url"])
    print(f"  {status}  {t['url'][:80]}")
    print(f"    title: {t['title'][:60]}")

# ── Bund ───────────────────────────────────────────────────────────────────
print("\n=== Bund (TED Germany) ===")
from connectors.bund import BundConnector
bc = BundConnector(delay=0.5, max_pages=1)
tenders_bund = bc.fetch_recent(days_back=30)
print(f"  Tenders: {len(tenders_bund)}")
for t in tenders_bund[:3]:
    status = check_url(t["url"])
    print(f"  {status}  {t['url'][:80]}")
    print(f"    title: {t['title'][:60]}")
