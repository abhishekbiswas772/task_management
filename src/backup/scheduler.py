"""
Periodic database backup using APScheduler + pg_dump.
Runs every N hours, keeps the last BACKUP_KEEP_COUNT .sql.gz files.
Requires pg_dump (postgresql-client) to be installed in the container.
"""
from __future__ import annotations

import gzip
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _do_backup(database_url: str, backup_dir: str, keep: int = 20) -> None:
    """Run pg_dump and write a gzip-compressed SQL file, then prune old copies."""
    if not database_url.startswith("postgresql"):
        logger.warning("Backup skipped — not a Postgres URL.")
        return

    if not shutil.which("pg_dump"):
        logger.warning("Backup skipped — pg_dump not found in PATH.")
        return

    try:
        dst_dir = Path(backup_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)

        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_dir / f"taskboard_{ts}.sql.gz"

        result = subprocess.run(
            ["pg_dump", "--no-password", database_url],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace"))

        with gzip.open(dst, "wb") as gz:
            gz.write(result.stdout)

        logger.info("Backup written: %s (%d KB)", dst, dst.stat().st_size // 1024)

        # Prune oldest backups beyond keep limit
        backups = sorted(dst_dir.glob("taskboard_*.sql.gz"))
        for old in backups[:-keep]:
            old.unlink(missing_ok=True)
            logger.info("Pruned old backup: %s", old)

    except Exception as exc:
        logger.error("Backup failed: %s", exc)


def start_scheduler(app) -> None:
    """Start the background scheduler; safe to call only once."""
    global _scheduler
    if _scheduler is not None:
        return

    if not app.config.get("DB_BACKUP_ENABLED", False):
        logger.info("Database backup scheduler disabled.")
        return

    database_url = app.config.get("SYNC_DATABASE_URI", "")
    backup_dir   = app.config["BACKUP_DIR"]
    interval     = app.config.get("BACKUP_INTERVAL_HOURS", 6)
    keep         = app.config.get("BACKUP_KEEP_COUNT", 20)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=_do_backup,
        trigger="interval",
        hours=interval,
        args=[database_url, backup_dir, keep],
        id="db_backup",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info(
        "Backup scheduler started — every %sh, keeping %s copies → %s",
        interval, keep, backup_dir,
    )

    import atexit
    atexit.register(_shutdown)


def _shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Backup scheduler stopped.")
