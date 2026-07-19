import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.brand import BrandSpace

async def main():
    # Set console encoding to UTF-8
    sys.stdout.reconfigure(encoding='utf-8')
    async with AsyncSessionLocal() as session:
        stmt = select(BrandSpace).where(BrandSpace.id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74')
        res = await session.execute(stmt)
        brand = res.scalar_one_or_none()
        if brand:
            print("Brand Name:", brand.name)
            context = brand.resolved_brand_context or {}
            
            # Print identity keys
            identity = context.get("identity") or {}
            print("Identity keys:", list(identity.keys()))
            print("Logo selection:", identity.get("logo_selection"))
            print("Logo asset path:", identity.get("logo_asset_path"))
        else:
            print("Brand space not found")

if __name__ == '__main__':
    asyncio.run(main())
