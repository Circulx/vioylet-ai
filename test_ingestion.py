"""Test script to verify document ingestion pipeline."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.vectorstore.ingestion_service import IngestionService
from app.core.config import get_settings

def test_ingestion_pipeline():
    """Test the ingestion pipeline with a user-provided document."""
    settings = get_settings()
    
    print("=" * 60)
    print("Document Ingestion Pipeline Test")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Configuration Check:")
    print(f"   - OpenAI API Key: {'✓ Set' if settings.openai_api_key else '✗ Missing'}")
    print(f"   - Pinecone API Key: {'✓ Set' if settings.pinecone_api_key else '✗ Missing'}")
    print(f"   - Pinecone Index: {settings.pinecone_index_name}")
    print(f"   - Embedding Model: {settings.ingestion_embedding_model}")
    print(f"   - Chunk Size: {settings.ingestion_chunk_size}")
    
    if not settings.openai_api_key:
        print("\n⚠ WARNING: OpenAI API key not set. Classification and embedding will fail.")
    
    if not settings.pinecone_api_key:
        print("\n⚠ WARNING: Pinecone API key not set. Vector storage will fail.")
    
    # Initialize service
    print("\n2. Initializing IngestionService...")
    try:
        service = IngestionService()
        print("   ✓ Service initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return False
    
    # Check client initialization
    print("\n3. Client Status:")
    print(f"   - OpenAI Client: {'✓ Initialized' if service.openai_client else '✗ Not initialized'}")
    print(f"   - Pinecone Client: {'✓ Initialized' if service.pinecone_client else '✗ Not initialized'}")
    print(f"   - Pinecone Index: {'✓ Connected' if service.pinecone_index else '✗ Not connected'}")
    
    # Ask user for document path
    print("\n4. Document Selection:")
    print("   Please provide the path to a document file (DOCX, PDF, or TXT)")
    print("   Example: C:\\path\\to\\your\\document.pdf")
    
    file_path = input("   Enter file path: ").strip()
    
    if not file_path:
        print("   ✗ No file path provided")
        return False
    
    test_doc_path = Path(file_path)
    
    if not test_doc_path.exists():
        print(f"   ✗ File not found: {test_doc_path}")
        return False
    
    print(f"   ✓ Document selected: {test_doc_path}")
    
    # Test parsing
    print("\n5. Testing document parsing...")
    try:
        text = service.parse_document(str(test_doc_path))
        print(f"   ✓ Parsed {len(text)} characters")
        print(f"   First 100 chars: {text[:100]}...")
    except Exception as e:
        print(f"   ✗ Parsing failed: {e}")
        return False
    
    # Test chunking
    print("\n6. Testing text chunking...")
    try:
        chunks = service.chunk_text(text)
        print(f"   ✓ Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks[:3]):
            print(f"   Chunk {i+1}: {len(chunk)} chars - {chunk[:50]}...")
    except Exception as e:
        print(f"   ✗ Chunking failed: {e}")
        return False
    
    # Test classification (requires OpenAI)
    print("\n7. Testing chunk classification...")
    if service.openai_client:
        try:
            classification = service.classify_chunk(chunks[0])
            print(f"   ✓ Classification successful:")
            print(f"     - Category: {classification['category']}")
            print(f"     - Section: {classification['section']}")
            print(f"     - Influence Area: {classification['influence_area']}")
            print(f"     - Summary: {classification['content_summary']}")
        except Exception as e:
            print(f"   ✗ Classification failed: {e}")
    else:
        print("   ⊘ Skipped (OpenAI client not initialized)")
    
    # Test embedding (requires OpenAI)
    print("\n8. Testing embedding generation...")
    if service.openai_client:
        try:
            embedding = service.generate_embedding(chunks[0])
            print(f"   ✓ Embedding generated:")
            print(f"     - Dimensions: {len(embedding)}")
            print(f"     - First 5 values: {embedding[:5]}")
        except Exception as e:
            print(f"   ✗ Embedding failed: {e}")
    else:
        print("   ⊘ Skipped (OpenAI client not initialized)")
    
    # Test Pinecone upsert (requires Pinecone)
    print("\n9. Testing Pinecone upsert...")
    if service.pinecone_index and service.openai_client:
        try:
            test_brand_id = "test_brand_123"
            classified_chunks = []
            for chunk in chunks:
                classification = service.classify_chunk(chunk)
                classified_chunks.append({
                    "content": chunk,
                    "category": classification["category"],
                    "section": classification["section"],
                    "influence_area": classification["influence_area"],
                    "content_summary": classification["content_summary"],
                })
            
            service.upsert_to_pinecone(test_brand_id, classified_chunks)
            print(f"   ✓ Upserted {len(classified_chunks)} chunks to Pinecone")
        except Exception as e:
            print(f"   ✗ Upsert failed: {e}")
    else:
        print("   ⊘ Skipped (Pinecone index or OpenAI client not initialized)")
    
    # Test search (requires both OpenAI and Pinecone)
    print("\n10. Testing Pinecone search...")
    if service.pinecone_index and service.openai_client:
        try:
            results = service.search_pinecone("test_brand_123", "brand colors", top_k=3)
            print(f"   ✓ Search returned {len(results)} results")
            for i, result in enumerate(results):
                print(f"   Result {i+1}:")
                print(f"     - Score: {result['score']:.4f}")
                print(f"     - Category: {result['category']}")
                print(f"     - Section: {result['section']}")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")
    else:
        print("   ⊘ Skipped (Pinecone index or OpenAI client not initialized)")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        test_ingestion_pipeline()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
