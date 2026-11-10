"""
Daemon process entrypoint for the HealCloud Background Worker.
Executes due health checks on a configurable polling interval with graceful shutdown.
"""

import signal
import sys
import time
from app.core.logging import logger
from app.worker.runner import run_pending_checks

_keep_running = True


def handle_shutdown(signum, frame):
    global _keep_running
    logger.info("Worker received shutdown signal. Terminating worker loop gracefully...")
    _keep_running = False


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Starting HealCloud Background Monitoring Worker daemon...")
    while _keep_running:
        try:
            executed = run_pending_checks()
            if executed > 0:
                logger.info("Processed %d health checks in this cycle.", executed)
        except Exception as exc:
            logger.error("Error during worker execution cycle: %s", exc, exc_info=True)

        time.sleep(5)

    logger.info("HealCloud Worker daemon exited cleanly.")


if __name__ == "__main__":
    main()

