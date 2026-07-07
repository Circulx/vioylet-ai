"""Check Pinecone vector count for a specific brand namespace."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

INDEX_NAME = "newbrandlove"


def main(brand_id: str) -> None:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    index = pc.Index(INDEX_NAME)
    namespace = f"brand:{brand_id}"

    stats = index.describe_index_stats()
    vector_count = stats.namespaces.get(namespace, {}).get("vector_count", 0)

    print(f"Index: {INDEX_NAME}")
    print(f"Brand ID: {brand_id}")
    print(f"Namespace: {namespace}")
    print(f"Vector count: {vector_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_pinecone_count.py <brand_id>")
        sys.exit(1)
    main(sys.argv[1])
