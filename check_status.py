import asyncio
import os
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset

async def check_brand_status(brand_id):
    async with AsyncSessionLocal() as session:
        # Check overall asset status
        query = select(KnowledgeAsset.lifecycle_state, func.count()).where(
            KnowledgeAsset.brand_space_id == brand_id
        ).group_by(KnowledgeAsset.lifecycle_state)
        
        result = await session.execute(query)
        stats = result.all()
        
        print(f"Status for Brand {brand_id}:")
        for state, count in stats:
            print(f"  - {state}: {count}")
            
        # Check for any processing errors
        error_query = select(KnowledgeAsset.name, KnowledgeAsset.processing_error).where(
            KnowledgeAsset.brand_space_id == brand_id,
            KnowledgeAsset.processing_error.isnot(None)
        )
        errors = await session.execute(error_query)
        error_list = errors.all()
        if error_list:
            print("\nRecent Errors:")
            for name, err in error_list[:5]:
                print(f"  - {name}: {err}")

if __name__ == "__main__":
    brand_id = "1eeb4475-24ca-41dd-8cad-80bb50e0ca74"
    asyncio.run(check_brand_status(brand_id))
