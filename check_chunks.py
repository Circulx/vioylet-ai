import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset

async def check_chunks():
    async with AsyncSessionLocal() as session:
        # Check overall asset status
        query = select(KnowledgeAsset.lifecycle_state, func.count()).where(
            KnowledgeAsset.brand_space_id == '1eeb4475-24ca-41dd-8cad-80bb50e0ca74'
        ).group_by(KnowledgeAsset.lifecycle_state)
        
        result = await session.execute(query)
        stats = result.all()
        
        print("Document Status:")
        for state, count in stats:
            print(f"  - {state}: {count}")

        # Try to estimate chunk count from metadata if available, or just look at Pinecone
        # Since I can't easily query Pinecone by brand AND count without fetching all, 
        # I'll just report what I found from the view_pinecone.py script.

if __name__ == "__main__":
    asyncio.run(check_chunks())
