"""
Background Worker Execution Runner for Scheduled Health Checks
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.service import MonitoringCheck
from app.services.health_checker import execute_monitoring_check

logger = logging.getLogger("healcloud.worker")


def run_pending_checks(db: Optional[Session] = None, max_checks: int = 50) -> int:
    """
    Identifies active health checks due for execution and runs probes sequentially.
    Returns the count of executed checks.
    """
    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        now = datetime.now(timezone.utc)
        
        # Query enabled checks
        checks = (
            db.query(MonitoringCheck)
            .filter(MonitoringCheck.is_enabled.is_(True))
            .all()
        )

        due_checks = []
        for c in checks:
            if c.last_checked_at is None:
                due_checks.append(c)
            else:
                last_checked = c.last_checked_at
                if last_checked.tzinfo is None:
                    last_checked = last_checked.replace(tzinfo=timezone.utc)
                if last_checked + timedelta(seconds=c.interval_seconds) <= now:
                    due_checks.append(c)

        executed_count = 0
        for check in due_checks[:max_checks]:
            try:
                sample = execute_monitoring_check(check.id, db=db)
                executed_count += 1
                logger.info(
                    f"Health check executed for service {check.service_id}: "
                    f"success={sample.is_successful}, time={sample.response_time_ms}ms"
                )
            except Exception as exc:
                logger.error(f"Error executing health check {check.id}: {exc}")

        if executed_count > 0:
            db.commit()

        return executed_count
    finally:
        if close_after:
            db.close()

