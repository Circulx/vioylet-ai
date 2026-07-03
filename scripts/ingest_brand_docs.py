"""Ingest brand documents from a local folder into Pinecone.

Usage:
    python scripts/ingest_brand_docs.py <folder_path> [brand_id]

If brand_id is not provided, defaults to the WWE brand UUID.
Supported file types: .txt, .pdf, .docx, .md, .csv, .json
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BRAND_ID = "f5072038-e3b5-40de-8d49-c074fe5015d6"


async def ingest(folder_path: str, brand_id: str) -> None:
    from app.services.vectorstore.ingestion_service import IngestionService

    folder = Path(folder_path)
    if not folder.exists():
        print(f"ERROR: Folder does not exist: {folder}")
        return

    files = []
    for ext in ["*.txt", "*.pdf", "*.docx", "*.md", "*.csv", "*.json"]:
        files.extend(folder.glob(f"**/{ext}"))

    if not files:
        print(f"ERROR: No supported files found in: {folder}")
        print("Supported: .txt, .pdf, .docx, .md, .csv, .json")
        return

    print(f"Found {len(files)} files to ingest:")
    for f in files:
        print(f"  {f.name}")

    service = IngestionService()
    total_chunks = 0

    for file_path in files:
        print(f"\nIngesting: {file_path.name}...")
        try:
            result = service.process_document(brand_id, str(file_path))
            total_chunks += result["total_chunks"]
            print(f"  -> {result['total_chunks']} chunks ingested")
            print(f"     categories: {', '.join(result['categories'])}")
            print(f"     influence_areas: {', '.join(result['influence_areas'])}")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    print(f"\nDone! Total chunks ingested: {total_chunks}")
    print(f"Brand ID: {brand_id}")
    print(f"Pinecone namespace: brand:{brand_id}")
    print(f"\nNow test retrieval at: http://localhost:3000/brand-retrieval")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "brand_docs"
    brand_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BRAND_ID
    asyncio.run(ingest(folder, brand_id))
