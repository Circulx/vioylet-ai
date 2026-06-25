# Operational scripts run one-off maintenance, smoke checks, and local debugging workflows.
import asyncio

from app.db.session import AsyncSessionLocal
from app.services.bootstrap import seed_rbac


async def main() -> None:
    # Command-line entrypoint that wires arguments and configuration into this script workflow.
    async with AsyncSessionLocal() as session:
        await seed_rbac(session)


if __name__ == "__main__":
    asyncio.run(main())

