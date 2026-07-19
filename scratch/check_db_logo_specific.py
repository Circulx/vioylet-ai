import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset

async def main():
    async with AsyncSessionLocal() as session:
        # Query specifically for any asset containing 'logo' or 'images' in name or path
        stmt = select(KnowledgeAsset).where(
            (KnowledgeAsset.brand_space_id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74') &
            ((KnowledgeAsset.name.ilike('%logo%')) | 
             (KnowledgeAsset.name.ilike('%image%')) | 
             (KnowledgeAsset.storage_path.ilike('%logo%')) | 
             (KnowledgeAsset.storage_path.ilike('%image%')))
        )
        res = await session.execute(stmt)
        assets = res.scalars().all()
        print("--- Matching Knowledge Assets ---")
        for asset in assets:
            print(f"ID: {asset.id}, Name: {asset.name}, Category: {asset.asset_category}, Field: {asset.field_key}, Path: {asset.storage_path}")

if __name__ == '__main__':
    asyncio.run(main())
