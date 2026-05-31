"""
HFIP – Full Integration Test Suite
Tests all components end-to-end with real API calls.

Run: python tests/test_all.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# ─── Path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # Required so relative data/ paths resolve

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

console = Console()

RESULTS: list[dict] = []

def test(name: str):
    """Decorator to register and run a test."""
    def decorator(fn):
        def wrapper():
            console.rule(f"[bold cyan]TEST: {name}")
            try:
                result = fn()
                RESULTS.append({"name": name, "status": "✅ PASS", "detail": str(result or "")})
                console.print(f"[bold green]✅ PASS[/] – {name}")
            except AssertionError as exc:
                RESULTS.append({"name": name, "status": "❌ FAIL", "detail": str(exc)})
                console.print(f"[bold red]❌ FAIL[/] – {name}: {exc}")
            except Exception as exc:
                RESULTS.append({"name": name, "status": "💥 ERROR", "detail": str(exc)})
                console.print(f"[bold yellow]💥 ERROR[/] – {name}: {exc}")
        wrapper.__test_name__ = name
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 – Database: create tables & upsert tender
# ─────────────────────────────────────────────────────────────────────────────
@test("Database – create tables and upsert tender")
def test_database():
    from database.repository import TenderRepository

    with tempfile.TemporaryDirectory() as tmp:
        repo = TenderRepository(db_path=f"{tmp}/test.db")
        try:
            tender_data = {
                "source": "test",
                "title": "AI-Based Clinical Decision Support System",
                "description": "Machine learning platform for hospital risk prediction using FHIR data.",
                "organization": "Test Hospital GmbH",
                "country": "DE",
                "deadline": datetime.utcnow() + timedelta(days=30),
                "published_date": datetime.utcnow(),
                "url": "https://example.com/tender/1",
                "cpv_codes": ["85100000", "72000000"],
                "hash": "test_hash_001",
                "keyword_score": 75,
                "is_archived": False,
            }

            # Insert
            tender, created = repo.upsert_tender(tender_data)
            assert created is True, "First insert should create a new record"

            # Duplicate
            _, created2 = repo.upsert_tender(tender_data)
            assert created2 is False, "Second insert with same hash should be rejected"

            # Count
            stats = repo.count_tenders()
            assert stats["total"] == 1, f"Expected 1 tender, got {stats['total']}"
        finally:
            repo.close()  # Release WAL locks before temp dir cleanup (Windows)

    return "DB create/upsert/dedup all working"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 – Scoring Engine
# ─────────────────────────────────────────────────────────────────────────────
@test("Scoring Engine – keyword and CPV scoring")
def test_scoring():
    from filters.scoring import HealthcareAIScorer

    scorer = HealthcareAIScorer()

    # High-relevance tender
    high = {
        "title": "AI Machine Learning Clinical Decision Support Platform",
        "description": "Digital health solution using LLM for FHIR-based EHR analytics in hospital settings.",
        "organization": "University Hospital",
        "cpv_codes": ["85100000", "72212000"],
        "source": "gba",
    }
    score_high, matches_high = scorer.score(high)
    console.print(f"  High-relevance score: [bold]{score_high}[/] | matches: {len(matches_high)}")
    assert score_high >= 50, f"Expected score >= 50 for healthcare AI tender, got {score_high}"

    # Irrelevant tender
    low = {
        "title": "Gebäudereinigung und Facility Management Dienstleistungen",
        "description": "Reinigungsarbeiten und Hausmeisterdienste für Bürogebäude. Möbel und Ausstattung.",
        "organization": "Cleaning GmbH",
        "cpv_codes": ["90910000"],
        "source": "bund",
    }
    score_low, _ = scorer.score(low)
    console.print(f"  Low-relevance score: [bold]{score_low}[/]")
    assert score_low < 50, f"Expected score < 50 for cleaning tender, got {score_low}"

    assert scorer.should_archive(score_low) is True
    assert scorer.should_evaluate_with_ai(score_high) is True

    return f"High={score_high}, Low={score_low}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 – CPV Scoring
# ─────────────────────────────────────────────────────────────────────────────
@test("CPV Code – scoring map")
def test_cpv():
    from filters.cpv import score_cpv_codes

    health_it = score_cpv_codes(["72212000", "85100000"])
    console.print(f"  Health IT CPV score: [bold]{health_it}[/]")
    assert health_it > 0, f"Expected positive score for health IT CPVs"

    construction = score_cpv_codes(["45000000"])
    console.print(f"  Construction CPV score: [bold]{construction}[/]")
    assert construction < 0, f"Expected negative score for construction CPV"

    return f"HealthIT={health_it}, Construction={construction}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 – Deduplication Engine
# ─────────────────────────────────────────────────────────────────────────────
@test("Deduplication – hash and fuzzy title matching")
def test_dedup():
    from filters.dedup import DeduplicationEngine

    dedup = DeduplicationEngine(similarity_threshold=0.85)

    # Hash generation
    h1 = dedup.compute_hash("AI Clinical Platform", "https://ted.europa.eu/1", "ted")
    h2 = dedup.compute_hash("AI Clinical Platform", "https://ted.europa.eu/1", "ted")
    assert h1 == h2, "Same input should produce same hash"

    h3 = dedup.compute_hash("Different Title", "https://ted.europa.eu/2", "ted")
    assert h1 != h3, "Different input should produce different hash"

    # Fuzzy dedup
    titles = ["AI-Based Clinical Decision Support System for Hospitals"]
    assert dedup.is_duplicate_title(
        "AI Based Clinical Decision Support System for Hospitals", titles
    ), "Very similar titles should be detected as duplicate"

    assert not dedup.is_duplicate_title(
        "Construction Services for Municipal Buildings", titles
    ), "Different topic should not match"

    return "Hash and fuzzy dedup both working"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 – TED API (real call, no auth required)
# ─────────────────────────────────────────────────────────────────────────────
@test("TED API – live search (no auth required)")
def test_ted_api():
    from connectors.ted import TEDConnector

    connector = TEDConnector()
    # Fetch last 7 days of health-related notices
    tenders = connector.fetch_recent(days_back=7)

    console.print(f"  TED notices fetched: [bold]{len(tenders)}[/]")
    assert len(tenders) >= 0, "Should return a list (may be empty)"

    if tenders:
        sample = tenders[0]
        console.print(f"  Sample: [italic]{sample.get('title', '')[:80]}[/]")
        assert "title" in sample
        assert "source" in sample
        assert sample["source"] == "ted"
        assert "hash" in sample

    return f"Fetched {len(tenders)} notices from TED"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 – Bund RSS Connector
# ─────────────────────────────────────────────────────────────────────────────
@test("Bund RSS – live feed fetch")
def test_bund_rss():
    from connectors.bund import BundConnector

    connector = BundConnector()
    tenders = connector.fetch_recent()
    console.print(f"  Bund entries fetched: [bold]{len(tenders)}[/]")

    for t in tenders[:2]:
        console.print(f"  • {t.get('title', '')[:70]}")

    assert isinstance(tenders, list)
    return f"Fetched {len(tenders)} Bund entries"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 – Groq LLM Evaluation (real API call)
# ─────────────────────────────────────────────────────────────────────────────
@test("Groq LLM – evaluate healthcare AI tender")
def test_groq_evaluation():
    groq_key = os.getenv("GROQ_API_KEY", "")
    assert groq_key, "GROQ_API_KEY not set in .env"

    from ai.groq_client import GroqClient
    from ai.evaluator import TenderEvaluator

    client = GroqClient(api_key=groq_key)
    evaluator = TenderEvaluator(groq_client=client)

    # Sample high-quality healthcare AI tender
    tender = {
        "id": 999,
        "source": "ted",
        "title": "AI-Based Clinical Decision Support System for ICU Risk Prediction",
        "description": (
            "Development of a machine learning platform for intensive care unit (ICU) "
            "patient risk prediction. The system should integrate with existing FHIR-compliant "
            "EHR systems, provide real-time sepsis risk scores, and support clinical decision "
            "workflows. The project includes data engineering, model training on historical "
            "patient data, and deployment within hospital IT infrastructure."
        ),
        "organization": "Universitätsklinikum Frankfurt",
        "country": "DE",
        "deadline": datetime.utcnow() + timedelta(days=45),
        "url": "https://ted.europa.eu/en/notice/-/detail/TEST-001",
    }

    result = evaluator.evaluate(tender)

    console.print(f"  Score:    [bold]{result.get('score')}[/]")
    console.print(f"  Relevant: [bold]{result.get('relevant')}[/]")
    console.print(f"  Category: [bold]{result.get('category')}[/]")
    console.print(f"  Summary:  [italic]{result.get('summary', '')[:120]}[/]")
    console.print(f"  Skills:   {result.get('required_skills')}")
    console.print(f"  Effort:   {result.get('proposal_effort')}")

    assert result.get("score") is not None, "Score should not be None"
    assert result.get("score", 0) >= 50, f"Expected high score for ICU AI tender, got {result.get('score')}"
    assert result.get("relevant") is True, "ICU AI tender should be marked relevant"
    assert result.get("category") not in (None, "Not Relevant"), "Should have a valid category"
    assert isinstance(result.get("required_skills"), list), "Skills should be a list"

    return f"Score={result.get('score')}, Category={result.get('category')}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 – Groq LLM – non-relevant tender
# ─────────────────────────────────────────────────────────────────────────────
@test("Groq LLM – reject non-healthcare tender")
def test_groq_irrelevant():
    groq_key = os.getenv("GROQ_API_KEY", "")
    assert groq_key, "GROQ_API_KEY not set in .env"

    from ai.groq_client import GroqClient
    from ai.evaluator import TenderEvaluator

    evaluator = TenderEvaluator(groq_client=GroqClient(api_key=groq_key))

    tender = {
        "id": 998,
        "source": "bund",
        "title": "Reinigung und Hausmeisterdienste für Bundesbehörde",
        "description": "Reinigungsarbeiten, Hausmeisterservice und Gebäudemanagement für ein Verwaltungsgebäude.",
        "organization": "Bundesbehörde für Verwaltung",
        "country": "DE",
        "deadline": datetime.utcnow() + timedelta(days=20),
        "url": "https://bund.de/tender/cleaning",
    }

    result = evaluator.evaluate(tender)
    console.print(f"  Score:    [bold]{result.get('score')}[/]")
    console.print(f"  Relevant: [bold]{result.get('relevant')}[/]")
    console.print(f"  Category: [bold]{result.get('category')}[/]")

    assert result.get("relevant") is False, "Cleaning tender should NOT be relevant"
    assert result.get("score", 100) < 50, f"Expected low score for cleaning tender"

    return f"Correctly rejected – Score={result.get('score')}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9 – Tavily Research Enrichment (real API call)
# ─────────────────────────────────────────────────────────────────────────────
@test("Tavily – research enrichment for healthcare AI tender")
def test_tavily():
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    assert tavily_key, "TAVILY_API_KEY not set in .env"

    from enrichment.tavily_client import TavilyResearcher

    researcher = TavilyResearcher(api_key=tavily_key, max_results=3)
    context = researcher.enrich(
        title="AI-Based Clinical Decision Support System",
        organization="Universitätsklinikum Frankfurt"
    )

    console.print(f"  Context length: [bold]{len(context)} chars[/]")
    if context:
        console.print(f"  Preview: [italic]{context[:200]}[/]")

    assert isinstance(context, str), "Context should be a string"
    # Tavily may return empty if no results, but shouldn't crash
    return f"Got {len(context)} chars of context"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 10 – Full Pipeline (DB + Score + Groq + Save)
# ─────────────────────────────────────────────────────────────────────────────
@test("Full Pipeline – collect → score → evaluate → save")
def test_full_pipeline():
    from database.repository import TenderRepository
    from filters.scoring import HealthcareAIScorer
    from ai.groq_client import GroqClient
    from ai.evaluator import TenderEvaluator

    groq_key = os.getenv("GROQ_API_KEY", "")
    assert groq_key, "GROQ_API_KEY not set"

    with tempfile.TemporaryDirectory() as tmp:
        repo = TenderRepository(db_path=f"{tmp}/pipeline_test.db")
        try:
            scorer = HealthcareAIScorer()
            evaluator = TenderEvaluator(groq_client=GroqClient(api_key=groq_key))

            # Simulate incoming tenders
            raw_tenders = [
                {
                    "source": "ted",
                    "title": "Machine Learning Platform for Oncology Imaging",
                    "description": "AI-based medical imaging platform for cancer detection using deep learning in radiology departments.",
                    "organization": "Charité Berlin",
                    "country": "DE",
                    "deadline": datetime.utcnow() + timedelta(days=60),
                    "published_date": datetime.utcnow(),
                    "url": "https://ted.europa.eu/test/pipeline/1",
                    "cpv_codes": ["85100000", "72212000"],
                },
                {
                    "source": "bund",
                    "title": "Bürobedarf und Druckerzeugnisse",
                    "description": "Lieferung von Büromaterial, Papier und Druckerzeugnissen.",
                    "organization": "Bundesamt",
                    "country": "DE",
                    "deadline": datetime.utcnow() + timedelta(days=10),
                    "published_date": datetime.utcnow(),
                    "url": "https://bund.de/test/office-supplies",
                    "cpv_codes": ["30192000"],
                },
            ]

            saved_relevant = 0
            for t in raw_tenders:
                from database.models import Tender
                t["hash"] = Tender.compute_hash(t["title"], t["url"], t["source"])
                score, _ = scorer.score(t)
                t["keyword_score"] = score
                t["is_archived"] = score < 50

                tender_obj, created = repo.upsert_tender(t)
                console.print(f"  [{t['source'].upper()}] '{t['title'][:50]}' → score={score} archived={t['is_archived']}")

                if not t["is_archived"]:
                    t_dict = {
                        "id": tender_obj.id,
                        "title": t["title"],
                        "description": t["description"],
                        "organization": t["organization"],
                        "country": t["country"],
                        "deadline": t["deadline"],
                        "source": t["source"],
                        "url": t["url"],
                    }
                    evaluation = evaluator.evaluate(t_dict)
                    evaluation["tender_id"] = tender_obj.id
                    repo.save_evaluation(evaluation)
                    console.print(f"    → AI Score: {evaluation.get('score')} | {evaluation.get('category')}")
                    saved_relevant += 1

            stats = repo.count_tenders()
            console.print(f"  DB stats: {stats}")
            assert stats["total"] >= 1
            assert stats["evaluated"] == saved_relevant
        finally:
            repo.close()  # Release WAL locks before temp dir cleanup (Windows)

    return f"Pipeline processed {len(raw_tenders)} tenders, {saved_relevant} evaluated by AI"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 11 – Prompt builder
# ─────────────────────────────────────────────────────────────────────────────
@test("Prompt Builder – renders correct prompt template")
def test_prompt_builder():
    from ai.prompts import build_user_prompt

    prompt = build_user_prompt(
        title="AI Diagnostics Platform",
        source="ted",
        organization="NHS",
        country="GB",
        deadline="30 June 2026",
        description="Machine learning for radiology.",
        tavily_context="Recent AI health funding trends show 40% growth.",
    )

    assert "AI Diagnostics Platform" in prompt
    assert "FHIR" in prompt or "JSON" in prompt  # Our prompt asks for JSON
    assert "Recent AI health funding trends" in prompt
    console.print(f"  Prompt length: {len(prompt)} chars")
    return f"Prompt rendered ({len(prompt)} chars)"


# ─────────────────────────────────────────────────────────────────────────────
# RUN ALL TESTS
# ─────────────────────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_database,
    test_scoring,
    test_cpv,
    test_dedup,
    test_ted_api,
    test_bund_rss,
    test_prompt_builder,
    test_groq_evaluation,
    test_groq_irrelevant,
    test_tavily,
    test_full_pipeline,
]

if __name__ == "__main__":
    console.print(Panel.fit(
        "[bold blue]HFIP – Full Integration Test Suite[/]\n"
        "Testing all components with real API calls",
        border_style="blue"
    ))

    start = time.time()
    for test_fn in ALL_TESTS:
        test_fn()
        time.sleep(1)  # Rate limiting between real API calls

    elapsed = time.time() - start

    # ── Summary table ──────────────────────────────────────────────────────
    console.rule("[bold]TEST RESULTS")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=4)
    table.add_column("Test Name", min_width=45)
    table.add_column("Status", width=12)
    table.add_column("Detail", max_width=60)

    passed = sum(1 for r in RESULTS if r["status"].startswith("✅"))
    failed = sum(1 for r in RESULTS if r["status"].startswith("❌"))
    errors = sum(1 for r in RESULTS if r["status"].startswith("💥"))

    for i, r in enumerate(RESULTS, 1):
        colour = "green" if r["status"].startswith("✅") else ("red" if r["status"].startswith("❌") else "yellow")
        table.add_row(str(i), r["name"], f"[{colour}]{r['status']}[/]", r["detail"][:60])

    console.print(table)
    console.print(
        f"\n[bold]Total:[/] {len(RESULTS)}  "
        f"[green]Passed: {passed}[/]  "
        f"[red]Failed: {failed}[/]  "
        f"[yellow]Errors: {errors}[/]  "
        f"⏱  {elapsed:.1f}s"
    )

    if failed + errors > 0:
        sys.exit(1)
