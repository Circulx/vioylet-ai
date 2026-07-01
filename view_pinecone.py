"""View Pinecone vector database contents."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from pinecone import Pinecone

def view_pinecone_index():
    """View Pinecone index statistics and sample data."""
    settings = get_settings()
    
    print("=" * 60)
    print("Pinecone Vector Database Viewer")
    print("=" * 60)
    
    # Initialize Pinecone client
    if not settings.pinecone_api_key:
        print("\n✗ Pinecone API key not configured")
        return
    
    pc = Pinecone(api_key=settings.pinecone_api_key)
    
    # List all indexes
    print("\n1. Available Indexes:")
    indexes = pc.list_indexes()
    if indexes.indexes:
        for index in indexes.indexes:
            print(f"   - {index.name} (dimension: {index.dimension})")
    else:
        print("   No indexes found")
        return
    
    # Connect to the configured index
    index_name = settings.pinecone_index_name
    print(f"\n2. Connecting to index: {index_name}")
    
    try:
        index = pc.Index(index_name)
    except Exception as e:
        print(f"   ✗ Failed to connect: {e}")
        return
    
    # Get index statistics
    print("\n3. Index Statistics:")
    try:
        stats = index.describe_index_stats()
        print(f"   - Total vectors: {stats.get('total_vector_count', 0)}")
        print(f"   - Dimension: {stats.get('dimension', 'N/A')}")
        print(f"   - Namespaces: {list(stats.get('namespaces', {}).keys())}")
    except Exception as e:
        print(f"   ✗ Failed to get stats: {e}")
    
    # List namespaces
    print("\n4. Namespaces:")
    try:
        # Query without namespace to see all
        # We'll try to fetch from the test namespace we used
        test_namespace = "brand:test_brand_123"
        print(f"   Checking namespace: {test_namespace}")
        
        # Try to fetch some vectors
        try:
            # Fetch first few vectors from the namespace
            fetch_result = index.fetch(
                ids=["test_brand_123_chunk_0"],
                namespace=test_namespace
            )
            
            if fetch_result.vectors:
                print(f"   ✓ Found {len(fetch_result.vectors)} vectors in namespace")
                for vector_id, vector_data in fetch_result.vectors.items():
                    print(f"\n   Vector ID: {vector_id}")
                    print(f"   - Metadata: {vector_data.metadata}")
                    print(f"   - Dimension: {len(vector_data.values)}")
                    print(f"   - First 5 values: {vector_data.values[:5]}")
            else:
                print(f"   No vectors found in {test_namespace}")
                
                # Try to list all vectors by querying
                print(f"\n   Attempting to query all vectors...")
                query_result = index.query(
                    vector=[0.0] * 3072,  # Dummy vector
                    top_k=10,
                    include_metadata=True,
                    namespace=test_namespace
                )
                
                if query_result.matches:
                    print(f"   ✓ Found {len(query_result.matches)} vectors via query")
                    for match in query_result.matches:
                        print(f"\n   Vector ID: {match.id}")
                        print(f"   - Score: {match.score}")
                        print(f"   - Metadata: {match.metadata}")
                else:
                    print(f"   No vectors found")
                    
        except Exception as e:
            print(f"   ✗ Failed to fetch: {e}")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Try to get all namespaces
    print("\n5. All Namespace Statistics:")
    try:
        stats = index.describe_index_stats()
        namespaces = stats.get('namespaces', {})
        
        for namespace, ns_stats in namespaces.items():
            print(f"\n   Namespace: {namespace}")
            print(f"   - Vector count: {ns_stats.get('vector_count', 0)}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("View Complete")
    print("=" * 60)

if __name__ == "__main__":
    view_pinecone_index()
