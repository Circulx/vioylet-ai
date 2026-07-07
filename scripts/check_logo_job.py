"""Check jobs for the logo asset."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.collaboration import JobRecord


async def main() -> None:
    brand_id = "1eeb4475-24ca-41dd-8cad-80bb50e0ca74"
    asset_id = "a896c32b-c7de-46c9-8131-efefe949b8aa"
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(JobRecord)
            .where(JobRecord.brand_space_id == brand_id)
            .where(JobRecord.knowledge_asset_id == asset_id)
            .order_by(JobRecord.created_at.desc())
        )
        jobs = result.scalars().all()
        print(f"Jobs for logo asset: {len(jobs)}")
        for job in jobs:
            print(f"  {job.id} | {job.job_type} | {job.status} | {job.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
