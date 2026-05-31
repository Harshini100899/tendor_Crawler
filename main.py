"""
HFIP – Main Entry Point
Healthcare Funding Intelligence Platform

Usage:
    python main.py                    # Start scheduler + dashboard (production)
    python main.py --run-now          # Run full pipeline immediately then schedule
    python main.py --collect-only     # Run collection only (no AI evaluation)
    python main.py --evaluate-only    # Run AI evaluation only
    python main.py --dashboard-only   # Launch dashboard only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ─── Load environment ─────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ─── Logging setup ───────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()  # Remove default stderr handler
logger.add(
    sys.stderr,
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)
logger.add(
    LOG_DIR / "hfip_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="00:00",
    retention="30 days",
    compression="gz",
)

# ─── Local imports after path setup ──────────────────────────────────────────
from scheduler.scheduler import HFIPPipeline, HFIPScheduler


def start_dashboard() -> subprocess.Popen:
    """Launch Streamlit dashboard as a subprocess."""
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    logger.info("Starting Streamlit dashboard on http://localhost:8501 ...")
    return subprocess.Popen(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Healthcare Funding Intelligence Platform (HFIP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--run-now", action="store_true",
                        help="Run the full pipeline immediately")
    parser.add_argument("--collect-only", action="store_true",
                        help="Run data collection only (no AI evaluation)")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="Run AI evaluation only on pending tenders")
    parser.add_argument("--dashboard-only", action="store_true",
                        help="Launch dashboard without scheduler")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Run scheduler without launching dashboard")
    parser.add_argument("--db-path", type=str, default="data/hfip.db",
                        help="Path to SQLite database file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db_path

    logger.info("=" * 60)
    logger.info("  Healthcare Funding Intelligence Platform (HFIP) v1.0.0")
    logger.info("=" * 60)

    # ── Dashboard only ──────────────────────────────────────────────────────
    if args.dashboard_only:
        proc = start_dashboard()
        logger.info("Dashboard running. Press Ctrl+C to stop.")
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return

    # ── Collect only ────────────────────────────────────────────────────────
    if args.collect_only:
        pipeline = HFIPPipeline(db_path=db_path)
        pipeline.run_all_connectors()
        return

    # ── Evaluate only ───────────────────────────────────────────────────────
    if args.evaluate_only:
        pipeline = HFIPPipeline(db_path=db_path)
        pipeline.run_evaluation()
        return

    # ── Full production mode ────────────────────────────────────────────────
    scheduler = HFIPScheduler(db_path=db_path)

    # Optionally run pipeline immediately on startup
    if args.run_now:
        logger.info("Running initial full pipeline pass...")
        scheduler.run_now()

    # Start background scheduler
    scheduler.start()

    # Start Streamlit dashboard (unless --no-dashboard)
    dashboard_proc = None
    if not args.no_dashboard:
        dashboard_proc = start_dashboard()

    logger.info("HFIP is running. Scheduled jobs active.")
    logger.info("Dashboard: http://localhost:8501")
    logger.info("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down HFIP...")
        scheduler.stop()
        if dashboard_proc:
            dashboard_proc.terminate()
        logger.info("HFIP stopped.")


if __name__ == "__main__":
    main()
