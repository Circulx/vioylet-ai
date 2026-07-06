"""Reprocess existing KnowledgeAssets to sync them into Pinecone.

This script queries all KnowledgeAssets for a given brand_space_id and
reprocesses them through KnowledgeService.process_asset, which will:
- Re-run OCR (or use cached text if available)
- Chunk and embed the text
- Upsert vectors to Pinecone with brand-space category metadata

Use this to backfill existing documents after adding Pinecone ingestion.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset
from app.services.knowledge import KnowledgeService


async def main(brand_space_id: str | None = None) -> None:
    """Reprocess all assets for a given brand_space_id."""
    async with AsyncSessionLocal() as session:
        knowledge_service = KnowledgeService(session)

        # Build query
        query = select(KnowledgeAsset)
        if brand_space_id:
            query = query.where(KnowledgeAsset.brand_space_id == brand_space_id)
        
        result = await session.execute(query)
        assets = result.scalars().all()
        
        if not assets:
            print("No assets found.")
            if brand_space_id:
                print(f"  Brand space ID: {brand_space_id}")
            return

        print(f"Found {len(assets)} asset(s) to reprocess:")
        for asset in assets:
            print(f"  {asset.id} | {asset.original_filename} | {asset.field_key} | {asset.lifecycle_state}")

        # Confirm before proceeding (skip if --yes flag)
        import os
        if os.environ.get("AUTO_CONFIRM") != "1":
            if brand_space_id:
                confirm = input(f"\nReprocess all {len(assets)} assets for brand {brand_space_id}? (y/n): ")
            else:
                confirm = input(f"\nReprocess all {len(assets)} assets across all brands? (y/n): ")
            
            if confirm.lower() != "y":
                print("Aborted.")
                return
        else:
            print(f"\nAuto-confirm enabled. Reprocessing {len(assets)} assets...")

        # Reprocess each asset
        success_count = 0
        error_count = 0
        
        for i, asset in enumerate(assets, 1):
            print(f"\n[{i}/{len(assets)}] Processing {asset.original_filename}...")
            try:
                print(f"  → Starting process_asset...")
                await knowledge_service.process_asset(asset.id)
                print(f"  ✓ Processed successfully")
                success_count += 1
            except Exception as e:  # noqa: BLE001
                import traceback
                print(f"  ✗ Failed: {e}")
                traceback.print_exc()
                error_count += 1

        print(f"\n{'='*60}")
        print(f"Reprocessing complete:")
        print(f"  Success: {success_count}")
        print(f"  Errors:  {error_count}")
        print(f"  Total:   {len(assets)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    
    brand_id = None
    if len(sys.argv) > 1:
        brand_id = sys.argv[1]
        print(f"Reprocessing assets for brand_space_id: {brand_id}")
    else:
        print("Reprocessing assets for ALL brand spaces.")
        print("To target a specific brand, pass brand_space_id as argument:")
        print("  python scripts/reprocess_assets_to_pinecone.py <brand_space_id>")
    
    asyncio.run(main(brand_id))
