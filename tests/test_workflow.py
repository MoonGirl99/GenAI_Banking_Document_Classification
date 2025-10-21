#!/usr/bin/env python3
"""
Enhanced Test Script for Bank Document Classification System
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test if server is running"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Server is healthy: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False


def test_text_processing():
    """Test processing raw text input (copy-paste)"""
    print("\n📝 Testing text input processing...")

    test_text = """
    Sehr geehrte Damen und Herren,

    ich möchte mich über die schlechte Beratung in Ihrer Filiale beschweren.

    Am 15.10.2024 wurde mir ein falscher Kredit vermittelt.
    Kundennummer: KD-987654321
    IBAN: DE89370400440532013000

    Ich fordere eine sofortige Klärung und Entschädigung!

    Mit freundlichen Grüßen,
    Anna Schmidt
    """

    try:
        response = requests.post(
            f"{BASE_URL}/process-text",
            params={"text_input": test_text}
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Text processed successfully!")
            print(f"\n📊 Results:")
            print(f"  Document ID: {result.get('document_id')}")
            print(f"  Category: {result.get('category')} (Should be 'complaints')")
            print(f"  Urgency: {result.get('urgency')} (Should be 'high')")
            print(f"  Department: {result.get('department')}")
            return result.get('document_id')
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error processing text: {e}")
        return None


def test_document_upload():
    """Test document file upload"""
    print("\n📄 Testing document upload...")

    test_doc_content = """
    Antrag auf Kontoeröffnung

    Hiermit beantrage ich die Eröffnung eines Girokontos.

    Name: Thomas Weber
    Geburtsdatum: 01.01.1980
    Adresse: Hauptstraße 123, 12345 Berlin
    E-Mail: thomas.weber@example.de

    Bitte senden Sie mir die Unterlagen zu.
    """

    with open('/tmp/test_account.txt', 'w') as f:
        f.write(test_doc_content)

    try:
        with open('/tmp/test_account.txt', 'rb') as f:
            files = {'file': ('account_request.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/process-document", files=files)

        if response.status_code == 200:
            result = response.json()
            print("✅ Document uploaded and processed!")
            print(f"  Category: {result.get('category')} (Should be 'account_inquiries')")
            return result.get('document_id')
        else:
            print(f"❌ Upload failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error uploading document: {e}")
        return None


def test_search_with_threshold():
    """Test semantic search with similarity threshold"""
    print("\n🔎 Testing search with similarity threshold...")

    # Test 1: Search for relevant term (should find documents)
    print("\n  Test 1: Searching for 'Beschwerde' (complaint)...")
    try:
        response = requests.get(
            f"{BASE_URL}/search-documents",
            params={"query": "Beschwerde", "n_results": 5, "min_similarity": 0.6}
        )

        if response.status_code == 200:
            results = response.json()
            if results.get('results'):
                print(f"  ✅ Found {len(results['results'])} documents with >60% similarity")
                for result in results['results'][:2]:
                    print(f"    - Doc {result['document_id'][:8]}... Similarity: {result['similarity']:.2%}")
            else:
                print("  ℹ️ No documents found (expected if DB is empty)")
        elif response.status_code == 404:
            result = response.json()
            print(f"  ℹ️ {result.get('message')}")
    except Exception as e:
        print(f"  ❌ Search error: {e}")

    # Test 2: Search for unrelated term (should not find documents)
    print("\n  Test 2: Searching for 'Pizza Restaurant' (unrelated)...")
    try:
        response = requests.get(
            f"{BASE_URL}/search-documents",
            params={"query": "Pizza Restaurant", "n_results": 5, "min_similarity": 0.6}
        )

        if response.status_code == 404:
            result = response.json()
            print(f"  ✅ Correctly returned 404: {result.get('message')}")
        elif response.status_code == 200:
            results = response.json()
            if not results.get('results'):
                print("  ✅ No documents found (correct behavior)")
            else:
                print(f"  ⚠️ Found {len(results['results'])} documents (unexpected)")
    except Exception as e:
        print(f"  ❌ Search error: {e}")


def test_chromadb_gui():
    """Check if ChromaDB GUI is accessible"""
    print("\n🖥️ Checking ChromaDB GUI...")
    print("  ChromaDB Admin UI should be available at: http://localhost:3000")
    print("  You can use it to:")
    print("    - View all stored documents")
    print("    - See document embeddings and metadata")
    print("    - Run queries directly on the database")
    print("    - Monitor collection statistics")


def main():
    print("=" * 70)
    print("🧪 Enhanced Bank Document Classification System Test")
    print("=" * 70)

    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Server is not running. Please start with: docker compose up -d")
        return

    # Test 2: Process text input (copy-paste)
    text_doc_id = test_text_processing()

    # Wait for processing
    time.sleep(2)

    # Test 3: Upload document file
    file_doc_id = test_document_upload()

    # Wait for processing
    time.sleep(2)

    # Test 4: Search with similarity threshold
    test_search_with_threshold()

    # Test 5: Info about ChromaDB GUI
    test_chromadb_gui()

    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    print("\n📚 Resources:")
    print(f"  - API Documentation: {BASE_URL}/docs")
    print(f"  - ChromaDB GUI: http://localhost:3000")
    print(f"  - Direct ChromaDB API: http://localhost:8001")


if __name__ == "__main__":
    main()