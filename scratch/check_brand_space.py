import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.brand import BrandSpace

async def main():
    async with AsyncSessionLocal() as session:
        stmt = select(BrandSpace).where(BrandSpace.id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74')
        res = await session.execute(stmt)
        brand = res.scalar_one_or_none()
        if brand:
            print("Brand Name:", brand.name)
            print("Overview Snapshot:", brand.overview_snapshot)
            print("Resolved Brand Context:", brand.resolved_brand_context)
        else:
            print("Brand space not found")

if __name__ == '__main__':
    asyncio.run(main())
