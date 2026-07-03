"""View complete metadata for all vectors in a Pinecone namespace."""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

INDEX_NAME = "newbrandlove"
NAMESPACE = "brand:f5072038-e3b5-40de-8d49-c074fe5015d6"


def main() -> None:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(INDEX_NAME)

    stats = index.describe_index_stats()
    print(f"Index: {INDEX_NAME}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Namespace vector count: {stats.namespaces.get(NAMESPACE, {}).get('vector_count', 0)}")
    print()

    # Query all vectors with a zero vector and include_metadata=True
    dimension = stats.dimension
    zero_vector = [0.0] * dimension
    results = index.query(
        vector=zero_vector,
        namespace=NAMESPACE,
        top_k=1000,
        include_metadata=True,
    )

    metadata_map: dict[str, dict] = {}
    for match in results.matches:
        metadata_map[match.id] = dict(match.metadata)

    output_path = r"C:\Users\Lenovo\ai10\Violyt-ai\pinecone_metadata.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata_map, f, indent=2, ensure_ascii=False)
    print(f"\nWrote complete metadata for {len(metadata_map)} vectors to {output_path}")


if __name__ == "__main__":
    main()
