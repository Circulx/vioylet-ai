import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset
from app.models.brand_assets import BrandLogoAsset

async def main():
    async with AsyncSessionLocal() as session:
        # Check KnowledgeAsset
        stmt = select(KnowledgeAsset).where(KnowledgeAsset.brand_space_id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74')
        res = await session.execute(stmt)
        assets = res.scalars().all()
        print("--- Knowledge Assets ---")
        for asset in assets:
            print(f"ID: {asset.id}, Name: {asset.name}, Category: {asset.asset_category}, Field: {asset.field_key}, Path: {asset.storage_path}")

        # Check BrandLogoAsset
        stmt_logo = select(BrandLogoAsset).where(BrandLogoAsset.brand_space_id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74')
        res_logo = await session.execute(stmt_logo)
        logos = res_logo.scalars().all()
        print("--- Brand Logo Assets ---")
        for logo in logos:
            print(f"ID: {logo.id}, Knowledge ID: {logo.knowledge_asset_id}")

if __name__ == '__main__':
    asyncio.run(main())
