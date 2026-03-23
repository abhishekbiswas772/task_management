"""
Periodic database backup using APScheduler.
Runs every N hours, keeps the last BACKUP_KEEP_COUNT files.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _do_backup(db_path: str, backup_dir: str, keep: int = 20) -> None:
    """Copy the SQLite DB to backups/<timestamp>.db and prune old copies."""
    try:
        src = Path(db_path)
        if not src.exists():
            logger.warning("Backup skipped — DB not found: %s", db_path)
            return

        dst_dir = Path(backup_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)

        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_dir / f"tasks_backup_{ts}.db"
        shutil.copy2(src, dst)
        logger.info("Backup written: %s", dst)

        # Prune oldest backups beyond keep limit
        backups = sorted(dst_dir.glob("tasks_backup_*.db"))
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

    db_path    = app.config["DB_PATH"]
    backup_dir = app.config["BACKUP_DIR"]
    interval   = app.config.get("BACKUP_INTERVAL_HOURS", 6)
    keep       = app.config.get("BACKUP_KEEP_COUNT", 20)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=_do_backup,
        trigger="interval",
        hours=interval,
        args=[db_path, backup_dir, keep],
        id="db_backup",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("Backup scheduler started — every %sh, keeping %s copies", interval, keep)

    import atexit
    atexit.register(_shutdown)


def _shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Backup scheduler stopped.")
