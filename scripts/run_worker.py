# Operational scripts run one-off maintenance, smoke checks, and local debugging workflows.
import asyncio

from app.workers.runner import run_worker_loop


if __name__ == "__main__":
    asyncio.run(run_worker_loop())

