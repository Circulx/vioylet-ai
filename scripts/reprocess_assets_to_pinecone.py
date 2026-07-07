"""Sync existing KnowledgeAssets into Pinecone using already-extracted text.

This script bypasses OCR entirely and uses the extracted_text stored in the
database from prior processing. It pushes text directly to Pinecone via
IngestionService.ingest_asset_text, which chunks, embeds, and upserts.

Usage:
    python scripts/reprocess_assets_to_pinecone.py <brand_space_id>
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
from app.services.vectorstore.ingestion_service import IngestionService


async def main(brand_space_id: str) -> None:
    """Sync all assets for a brand_space_id into Pinecone using stored extracted_text."""
    async with AsyncSessionLocal() as session:
        query = select(KnowledgeAsset).where(KnowledgeAsset.brand_space_id == brand_space_id)
        result = await session.execute(query)
        assets = result.scalars().all()

        if not assets:
            print(f"No assets found for brand {brand_space_id}")
            return

        has_text = [a for a in assets if a.extracted_text]
        no_text = [a for a in assets if not a.extracted_text]

        print(f"Found {len(assets)} assets:")
        print(f"  With extracted_text: {len(has_text)}")
        print(f"  Without extracted_text: {len(no_text)} (will skip)")

        if not has_text:
            print("\nNo assets have extracted text. Run OCR first via the UI worker.")
            return

        print(f"\nSyncing {len(has_text)} assets to Pinecone...")

        ingestion = IngestionService()
        if not ingestion.pinecone_index:
            print("ERROR: Pinecone index not initialized. Check PINECONE_API_KEY.")
            return
        if not ingestion.openai_client:
            print("ERROR: OpenAI client not initialized. Check OPENAI_API_KEY.")
            return

        success_count = 0
        error_count = 0
        skipped_count = 0

        for i, asset in enumerate(has_text, 1):
            fname = asset.original_filename or "unknown"
            category = asset.field_key or asset.channel or asset.asset_category or "knowledge"
            text_len = len(asset.extracted_text or "")
            print(f"\n[{i}/{len(has_text)}] {fname}")
            print(f"  category={category}  text_length={text_len}")

            try:
                print(f"  → Calling ingest_asset_text...")
                result = await asyncio.to_thread(
                    ingestion.ingest_asset_text,
                    brand_id=str(asset.brand_space_id),
                    asset_id=str(asset.id),
                    text=asset.extracted_text,
                    category=category,
                    filename=fname,
                )
                upserted = result.get("total_chunks", 0)
                print(f"  ✓ Upserted {upserted} chunks to Pinecone")
                success_count += 1
            except Exception as e:
                import traceback
                print(f"  ✗ FAILED: {e}")
                traceback.print_exc()
                error_count += 1

        print(f"\n{'='*60}")
        print(f"Sync complete:")
        print(f"  Success: {success_count}")
        print(f"  Errors:  {error_count}")
        print(f"  Skipped (no text): {len(no_text)}")
        print(f"  Total:   {len(assets)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reprocess_assets_to_pinecone.py <brand_space_id>")
        sys.exit(1)

    brand_id = sys.argv[1]
    print(f"Syncing assets to Pinecone for brand_space_id: {brand_id}")
    asyncio.run(main(brand_id))
