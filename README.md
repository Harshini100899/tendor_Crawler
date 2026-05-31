# 🏥 Healthcare Funding Intelligence Platform (HFIP)

> Fully local, Dockerized platform that continuously monitors German and EU healthcare funding ecosystems, filters Healthcare AI opportunities, enriches them with Tavily research, evaluates strategic fit using Groq LLMs, and automatically notifies researchers via Teams or Email.

---

## 🏗️ Architecture

```
Scheduler (APScheduler)
    │
    ├── TED API          → EU procurement notices
    ├── Bund RSS         → German federal funding
    ├── G-BA Scraper     → Innovation Fund calls
    └── BMFTR Scraper    → BMBF/Förderportal calls
         │
         ▼
    Normalization Layer
         │
         ▼
    SQLite Database
         │
         ▼
    Deduplication Engine (SHA-256 + Jaccard fuzzy)
         │
         ▼
    Healthcare AI Keyword Scorer
    (keyword + CPV scoring, score < 50 → archived)
         │
         ▼
    Tavily Research Enrichment
         │
         ▼
    Groq LLM Evaluation (llama3-70b-8192)
         │
         ▼
    score ≥ 80 → Teams Alert + Email Alert
         │
         ▼
    Streamlit Dashboard (localhost:8501)
```

---

## 📁 Project Structure

```
hfip/
├── connectors/         # Data source connectors
│   ├── ted.py          # TED Europa API (official)
│   ├── bund.py         # Bund.de RSS feeds
│   ├── gba.py          # G-BA Innovationsfonds scraper
│   └── bmftr.py        # BMBF / Förderportal scraper
├── database/
│   ├── models.py       # SQLAlchemy ORM (tenders, evaluations, notifications)
│   └── repository.py   # All DB read/write operations
├── filters/
│   ├── keywords.py     # Positive/negative keyword dictionary
│   ├── cpv.py          # CPV code scoring map
│   ├── scoring.py      # Pre-AI rule engine
│   └── dedup.py        # SHA-256 + fuzzy deduplication
├── ai/
│   ├── groq_client.py  # Groq via OpenAI SDK
│   ├── prompts.py      # System + user prompt templates
│   └── evaluator.py    # LLM orchestration + JSON parsing
├── tavily/
│   └── tavily_client.py  # Tavily search enrichment
├── notifications/
│   ├── teams.py        # Teams Adaptive Card webhook
│   └── email.py        # SMTP HTML email
├── scheduler/
│   └── scheduler.py    # APScheduler + pipeline orchestrator
├── dashboard/
│   └── app.py          # Streamlit 4-page dashboard
├── config/
│   └── settings.yaml   # Central configuration
├── data/               # SQLite DB + logs (gitignored)
├── main.py             # Entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start

### 1. Clone & Configure

```bash
cd hfip
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Run Immediately (First Collection)

```bash
python main.py --run-now
```

### 4. Start Full Platform (Scheduler + Dashboard)

```bash
python main.py
```

Open **http://localhost:8501** in your browser.

---

## 🐳 Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f hfip
```

---

## ⚙️ CLI Options

| Flag | Description |
|------|-------------|
| `--run-now` | Run full pipeline immediately then start scheduler |
| `--collect-only` | Run all collectors, no AI evaluation |
| `--evaluate-only` | Run AI evaluation on pending tenders only |
| `--dashboard-only` | Launch Streamlit dashboard only |
| `--no-dashboard` | Run scheduler without dashboard |
| `--db-path PATH` | Custom SQLite database path |

---

## 🔑 Required API Keys

| Key | Where to Get | Purpose |
|-----|-------------|---------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | LLM evaluation |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Research enrichment |
| `TED_API_KEY` | [api.ted.europa.eu](https://api.ted.europa.eu) | EU procurement notices |
| `TEAMS_WEBHOOK_URL` | Teams channel → Manage Channel → Connectors | Alert notifications |

---

## 📊 Scoring System

### Pre-AI Keyword Engine

| Score Range | Action |
|-------------|--------|
| < 50 | Archived (no AI evaluation) |
| ≥ 50 | Sent to Groq for evaluation |
| AI Score ≥ 80 | Teams + Email alert sent |

### Sample Positive Keywords

| Keyword | Score |
|---------|-------|
| AI / Machine Learning / LLM | +10 |
| Clinical Decision Support | +10 |
| Digital Health | +9 |
| Medical Imaging | +9 |
| FHIR / EHR | +8 |

### Sample Negative Keywords

| Keyword | Score |
|---------|-------|
| Construction / Bauleistung | -25 |
| Cleaning / Reinigung | -20 |
| Furniture / Möbel | -15 |

---

## 🤖 Groq LLM Output Format

```json
{
  "relevant": true,
  "score": 91,
  "category": "Healthcare AI",
  "summary": "AI-based hospital prediction platform.",
  "required_skills": ["AI", "Machine Learning", "Healthcare Analytics"],
  "proposal_effort": "High",
  "consortium_required": true
}
```

---

## 📅 Schedule

| Job | Schedule |
|-----|----------|
| TED Collection | Daily 06:00 |
| Bund RSS | Daily 07:00 |
| G-BA Collection | Monday 08:00 |
| BMFTR Collection | Monday 09:00 |
| AI Evaluation | Daily 10:00 |

---

## 🛠️ Development Roadmap

- **Phase 1** – TED + Bund + SQLite (500+ tenders)
- **Phase 2** – G-BA + BMFTR + Deduplication (unified DB)
- **Phase 3** – Scoring + Dashboard (80%+ precision)
- **Phase 4** – Groq + Tavily + Alerts (fully automated)
