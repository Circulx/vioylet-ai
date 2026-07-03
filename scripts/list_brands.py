"""List brand spaces in the database."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.brand import BrandSpace


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BrandSpace))
        brands = result.scalars().all()
        print(f"Found {len(brands)} brand(s):")
        for brand in brands:
            print(f"  {brand.id} | {brand.name} | {brand.slug}")


if __name__ == "__main__":
    asyncio.run(main())
