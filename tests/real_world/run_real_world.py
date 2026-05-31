"""
HFIP – Real-World Test Runner
Runs all 25 real-world cases through the full pipeline:
  1. Keyword / CPV pre-scoring
  2. Groq LLM evaluation  (openai/gpt-oss-120b)
  3. Tavily enrichment    (optional – skipped if TAVILY_API_KEY missing)
  4. Results saved to test_results/ as JSON, CSV, and Markdown report

Usage:
    cd hfip
    python tests/real_world/run_real_world.py
    python tests/real_world/run_real_world.py --no-tavily   # skip enrichment
    python tests/real_world/run_real_world.py --dry-run     # score only, no LLM
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

RESULTS_DIR = ROOT / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────

def run(no_tavily: bool = False, dry_run: bool = False) -> list[dict]:
    from tests.real_world.cases import ALL_CASES
    from filters.scoring import HealthcareAIScorer
    from database.models import Tender

    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    scorer = HealthcareAIScorer()

    evaluator = None
    if not dry_run:
        if not groq_key:
            console.print("[red]GROQ_API_KEY not set – aborting LLM evaluation.[/]")
            sys.exit(1)
        from ai.groq_client import GroqClient
        from ai.evaluator import TenderEvaluator
        evaluator = TenderEvaluator(groq_client=GroqClient(api_key=groq_key))

    enricher = None
    if not no_tavily and not dry_run and tavily_key:
        from enrichment.tavily_client import TavilyResearcher
        enricher = TavilyResearcher(api_key=tavily_key)

    results: list[dict] = []

    console.print(Panel.fit(
        f"[bold blue]HFIP – Real-World Pipeline Test[/]\n"
        f"Cases: {len(ALL_CASES)} | Groq: {'✅' if evaluator else '⬛ dry-run'} | "
        f"Tavily: {'✅' if enricher else '⬛ skipped'}",
        border_style="blue"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Processing cases...", total=len(ALL_CASES))

        for case in ALL_CASES:
            case_id   = case["case_id"]
            title     = case["title"]
            is_rel    = case["expected_relevant"]
            min_score = case["expected_min_score"]

            progress.update(task, description=f"[{case_id}] {title[:55]}…")

            # ── 1. Compute hash ──────────────────────────────────────────────
            case["hash"] = Tender.compute_hash(case["title"], case["url"], case["source"])

            # ── 2. Pre-score ─────────────────────────────────────────────────
            kw_score, kw_matches = scorer.score(case)
            case["keyword_score"] = kw_score
            case["is_archived"] = kw_score < 0  # only archive strong negatives

            # ── 3. Tavily enrichment ─────────────────────────────────────────
            tavily_context = ""
            if enricher and not case.get("is_archived"):
                try:
                    tavily_context = enricher.enrich(title)
                    time.sleep(0.5)
                except Exception as exc:
                    console.print(f"  [yellow]Tavily skipped for {case_id}: {exc}[/]")

            # ── 4. LLM evaluation ────────────────────────────────────────────
            ai_result = {}
            if evaluator and not case.get("is_archived"):
                try:
                    ai_result = evaluator.evaluate({
                        "id": None,
                        "title": case["title"],
                        "description": case["description"],
                        "organization": case["organization"],
                        "country": case["country"],
                        "deadline": case["deadline"],
                        "source": case["source"],
                        "url": case["url"],
                        "tavily_context": tavily_context,
                    })
                    time.sleep(1)  # Rate-limit Groq
                except Exception as exc:
                    console.print(f"  [red]LLM error for {case_id}: {exc}[/]")
                    ai_result = {"score": 0, "relevant": False, "category": "Error",
                                 "summary": str(exc), "required_skills": []}

            # ── 5. Assertion checks ──────────────────────────────────────────
            ai_score    = ai_result.get("score", 0)
            ai_relevant = ai_result.get("relevant", False)
            ai_category = ai_result.get("category", "N/A")
            ai_summary  = ai_result.get("summary", "")
            ai_skills   = ai_result.get("required_skills", [])

            score_pass    = (ai_score >= min_score) if is_rel else (ai_score < 40)
            relevant_pass = (ai_relevant == is_rel) if evaluator else None
            kw_pass       = (kw_score >= 50) if is_rel else (kw_score < 50)

            if dry_run:
                overall = "✅ PASS" if kw_pass else "❌ FAIL"
            else:
                overall = "✅ PASS" if (score_pass and relevant_pass) else "❌ FAIL"

            result = {
                "case_id":            case_id,
                "title":              title,
                "url":                case["url"],
                "source":             case["source"],
                "country":            case["country"],
                "organization":       case["organization"],
                "expected_relevant":  is_rel,
                "expected_min_score": min_score,
                "keyword_score":      kw_score,
                "keyword_matches":    len(kw_matches),
                "kw_pass":            kw_pass,
                "ai_score":           ai_score,
                "ai_relevant":        ai_relevant,
                "ai_category":        ai_category,
                "ai_summary":         ai_summary[:200] if ai_summary else "",
                "ai_skills":          ", ".join(ai_skills[:4]) if ai_skills else "",
                "tavily_chars":       len(tavily_context),
                "score_pass":         score_pass,
                "relevant_pass":      relevant_pass,
                "overall":            overall,
            }
            results.append(result)

            status_icon = "✅" if overall == "✅ PASS" else "❌"
            console.print(
                f"  {status_icon} [bold]{case_id}[/] | KW={kw_score:+4d} | "
                f"AI={ai_score:3d} | rel={str(ai_relevant):<5} | {ai_category[:25]}"
            )
            progress.advance(task)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_json(results: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    console.print(f"  📄 JSON  → {path.relative_to(ROOT)}")


def save_csv(results: list[dict], path: Path) -> None:
    if not results:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    console.print(f"  📊 CSV   → {path.relative_to(ROOT)}")


def save_markdown(results: list[dict], path: Path, elapsed: float) -> None:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    passed  = sum(1 for r in results if r["overall"] == "✅ PASS")
    failed  = sum(1 for r in results if r["overall"] == "❌ FAIL")
    rel_ok  = sum(1 for r in results if r["expected_relevant"] and r["overall"] == "✅ PASS")
    irr_ok  = sum(1 for r in results if not r["expected_relevant"] and r["overall"] == "✅ PASS")
    avg_ai  = (sum(r["ai_score"] for r in results) / len(results)) if results else 0

    lines = [
        f"# HFIP Real-World Test Report",
        f"",
        f"> Generated: {now_str}  |  Runtime: {elapsed:.1f}s",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total cases | {len(results)} |",
        f"| ✅ Passed | **{passed}** |",
        f"| ❌ Failed | **{failed}** |",
        f"| Relevant cases (15) passed | {rel_ok}/15 |",
        f"| Irrelevant cases (10) passed | {irr_ok}/10 |",
        f"| Average AI score (all) | {avg_ai:.1f} |",
        f"| Pass rate | {100*passed/len(results):.0f}% |",
        f"",
        f"## Relevant Healthcare-AI Cases (Expected: score ≥ 60, relevant=True)",
        f"",
        f"| Case ID | Title | Source Link | KW | AI | Cat | Pass |",
        f"|---------|-------|-------------|----|----|-----|------|",
    ]

    for r in results:
        if not r["expected_relevant"]:
            continue
        icon  = "✅" if r["overall"] == "✅ PASS" else "❌"
        title = r["title"][:55] + "…" if len(r["title"]) > 55 else r["title"]
        url   = r.get("url", "")
        link  = f"[🔗 Open]({url})" if url else "—"
        lines.append(
            f"| {r['case_id']} | {title} | {link} | {r['keyword_score']:+d} | "
            f"{r['ai_score']} | {r['ai_category'][:20]} | {icon} |"
        )

    lines += [
        f"",
        f"## Irrelevant Cases (Expected: score < 40, relevant=False)",
        f"",
        f"| Case ID | Title | Source Link | KW | AI | Cat | Pass |",
        f"|---------|-------|-------------|----|----|-----|------|",
    ]

    for r in results:
        if r["expected_relevant"]:
            continue
        icon  = "✅" if r["overall"] == "✅ PASS" else "❌"
        title = r["title"][:55] + "…" if len(r["title"]) > 55 else r["title"]
        url   = r.get("url", "")
        link  = f"[🔗 Open]({url})" if url else "—"
        lines.append(
            f"| {r['case_id']} | {title} | {link} | {r['keyword_score']:+d} | "
            f"{r['ai_score']} | {r['ai_category'][:20]} | {icon} |"
        )

    lines += [
        f"",
        f"## Detailed AI Summaries (Relevant Cases)",
        f"",
    ]

    for r in results:
        if not r["expected_relevant"] or not r["ai_summary"]:
            continue
        url = r.get("url", "")
        lines.append(f"### {r['case_id']} – {r['title'][:70]}")
        if url:
            lines.append(f"🔗 **Source:** [{url}]({url})")
        lines.append(f"- **AI Score:** {r['ai_score']} | **Category:** {r['ai_category']}")
        if r["ai_skills"]:
            lines.append(f"- **Skills:** {r['ai_skills']}")
        lines.append(f"- **Summary:** {r['ai_summary']}")
        lines.append("")

    lines += [
        f"---",
        f"*Generated by HFIP test runner – model: `{os.getenv('GROQ_MODEL','openai/gpt-oss-120b')}`*",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print(f"  📝 MD    → {path.relative_to(ROOT)}")


def print_summary_table(results: list[dict]) -> None:
    table = Table(title="Real-World Test Results", show_header=True, header_style="bold magenta")
    table.add_column("Case", width=8)
    table.add_column("Title", min_width=35, max_width=45, no_wrap=True)
    table.add_column("Exp.", width=5)
    table.add_column("KW", width=6, justify="right")
    table.add_column("AI", width=5, justify="right")
    table.add_column("Category", width=20)
    table.add_column("KW✓", width=4)
    table.add_column("AI✓", width=4)
    table.add_column("Pass", width=5)
    table.add_column("URL", min_width=30, no_wrap=True)

    for r in results:
        exp_icon = "✅" if r["expected_relevant"] else "❌"
        kw_c = "green" if r["kw_pass"] else "red"
        ai_c = "green" if r.get("relevant_pass") else ("yellow" if r["relevant_pass"] is None else "red")
        ov_c = "green" if r["overall"] == "✅ PASS" else "red"
        url  = r.get("url", "")
        table.add_row(
            r["case_id"],
            r["title"][:43],
            exp_icon,
            f"[{kw_c}]{r['keyword_score']:+d}[/]",
            str(r["ai_score"]),
            r["ai_category"][:19],
            f"[{kw_c}]{'✅' if r['kw_pass'] else '❌'}[/]",
            f"[{ai_c}]{'✅' if r['relevant_pass'] else ('–' if r['relevant_pass'] is None else '❌')}[/]",
            f"[{ov_c}]{r['overall'][:2]}[/]",
            f"[link={url}][blue]{url[:55]}[/][/link]" if url else "—",
        )
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="HFIP real-world pipeline test runner")
    parser.add_argument("--no-tavily", action="store_true", help="Skip Tavily enrichment")
    parser.add_argument("--dry-run",   action="store_true", help="Pre-scoring only, skip LLM")
    args = parser.parse_args()

    start = time.time()
    results = run(no_tavily=args.no_tavily, dry_run=args.dry_run)
    elapsed = time.time() - start

    # ── Print table ──────────────────────────────────────────────────────────
    console.rule("[bold]RESULTS")
    print_summary_table(results)

    passed = sum(1 for r in results if r["overall"] == "✅ PASS")
    failed = sum(1 for r in results if r["overall"] == "❌ FAIL")
    console.print(
        f"\n[bold]Total:[/] {len(results)}  "
        f"[green]Passed: {passed}[/]  "
        f"[red]Failed: {failed}[/]  "
        f"⏱  {elapsed:.1f}s\n"
    )

    # ── Save outputs ─────────────────────────────────────────────────────────
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    console.rule("[bold]SAVING RESULTS")

    save_json(results,    RESULTS_DIR / f"{stamp}_results.json")
    save_csv(results,     RESULTS_DIR / f"{stamp}_results.csv")
    save_markdown(results, RESULTS_DIR / f"{stamp}_report.md", elapsed)

    # Always overwrite latest_report.md
    save_markdown(results, RESULTS_DIR / "latest_report.md", elapsed)
    console.print(f"\n  All results saved to [bold]test_results/[/]")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
