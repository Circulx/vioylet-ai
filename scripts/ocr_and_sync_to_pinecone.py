"""OCR + Pinecone sync for assets missing extracted_text.

This script processes all assets for a brand_space_id:
- Assets WITH extracted_text are synced directly to Pinecone
- Assets WITHOUT extracted_text get OCR first, then save text, then sync to Pinecone

This bypasses FAISS indexing to avoid the hanging issue.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

from sqlalchemy import select

from app.ai.rag.ocr import OCRService
from app.core.enums import AssetLifecycle
from app.db.session import AsyncSessionLocal
from app.integrations.object_storage import LocalObjectStorage
from app.models.knowledge import KnowledgeAsset
from app.services.vectorstore.ingestion_service import IngestionService


async def main(brand_space_id: str) -> None:
    async with AsyncSessionLocal() as session:
        query = select(KnowledgeAsset).where(KnowledgeAsset.brand_space_id == brand_space_id)
        result = await session.execute(query)
        assets = result.scalars().all()

        if not assets:
            print(f"No assets found for brand {brand_space_id}")
            return

        ocr = OCRService()
        storage = LocalObjectStorage()
        ingestion = IngestionService()

        if not ingestion.pinecone_index:
            print("ERROR: Pinecone index not initialized. Check PINECONE_API_KEY.")
            return
        if not ingestion.openai_client:
            print("ERROR: OpenAI client not initialized. Check OPENAI_API_KEY.")
            return

        has_text = [a for a in assets if a.extracted_text]
        no_text = [a for a in assets if not a.extracted_text]

        print(f"Found {len(assets)} assets:")
        print(f"  With text: {len(has_text)}")
        print(f"  Without text: {len(no_text)}")

        synced_count = 0
        ocr_count = 0
        ocr_failed = 0
        sync_failed = 0

        # First sync assets that already have text
        print(f"\n--- Syncing {len(has_text)} assets with existing text ---")
        for i, asset in enumerate(has_text, 1):
            fname = asset.original_filename or "unknown"
            category = asset.field_key or asset.channel or asset.asset_category or "knowledge"
            print(f"[{i}/{len(has_text)}] Syncing {fname}...")
            try:
                await asyncio.to_thread(
                    ingestion.ingest_asset_text,
                    brand_id=str(asset.brand_space_id),
                    asset_id=str(asset.id),
                    text=asset.extracted_text,
                    category=category,
                    filename=fname,
                )
                print(f"  ✓ Synced")
                synced_count += 1
            except Exception as e:
                print(f"  ✗ Sync failed: {e}")
                sync_failed += 1

        # Then OCR and sync assets without text
        print(f"\n--- OCR + syncing {len(no_text)} assets without text ---")
        for i, asset in enumerate(no_text, 1):
            fname = asset.original_filename or "unknown"
            category = asset.field_key or asset.channel or asset.asset_category or "knowledge"
            print(f"[{i}/{len(no_text)}] OCR {fname}...")
            try:
                absolute_path = storage.absolute_path(asset.storage_path)
                print(f"  → Path: {absolute_path}")
                extracted = await asyncio.to_thread(ocr.extract, str(absolute_path))
                text = extracted.get("text", "")
                if not text:
                    print(f"  ⚠ No text extracted")
                    asset.lifecycle_state = AssetLifecycle.FAILED
                    asset.processing_error = "No text extracted"
                    ocr_failed += 1
                else:
                    print(f"  ✓ Extracted {len(text)} characters")
                    asset.extracted_text = text
                    asset.extracted_summary = text[:1000]
                    asset.page_count = extracted.get("page_count", 1)
                    asset.lifecycle_state = AssetLifecycle.PROCESSED
                    ocr_count += 1

                    print(f"  → Syncing to Pinecone...")
                    await asyncio.to_thread(
                        ingestion.ingest_asset_text,
                        brand_id=str(asset.brand_space_id),
                        asset_id=str(asset.id),
                        text=text,
                        category=category,
                        filename=fname,
                    )
                    print(f"  ✓ Synced to Pinecone")
                    synced_count += 1

                asset.last_indexed_at = datetime.now(timezone.utc).isoformat()
                await session.commit()

            except Exception as e:
                import traceback
                print(f"  ✗ Failed: {e}")
                traceback.print_exc()
                asset.lifecycle_state = AssetLifecycle.FAILED
                asset.processing_error = str(e)
                await session.commit()
                ocr_failed += 1

        print(f"\n{'='*60}")
        print(f"Complete:")
        print(f"  Already synced: {synced_count}")
        print(f"  OCR + synced:    {ocr_count}")
        print(f"  OCR failed:      {ocr_failed}")
        print(f"  Sync failed:     {sync_failed}")
        print(f"  Total assets:    {len(assets)}")
        print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ocr_and_sync_to_pinecone.py <brand_space_id>")
        sys.exit(1)

    brand_id = sys.argv[1]
    print(f"Processing OCR + Pinecone sync for brand_space_id: {brand_id}")
    asyncio.run(main(brand_id))
