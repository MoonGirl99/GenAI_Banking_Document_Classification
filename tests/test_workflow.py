#!/usr/bin/env python3
"""
Test script for Bank Document Classification System
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

def test_document_processing():
    """Test document processing workflow"""
    print("\n📄 Testing document processing workflow...")

    # Create test document
    test_doc_content = """Sehr geehrte Damen und Herren,

hiermit beantrage ich ein Darlehen in Höhe von 50.000 EUR für den Kauf eines Fahrzeugs.

Kundennummer: KD-123456789
Kontonummer: DE89370400440532013000
Name: Max Mustermann
E-Mail: max.mustermann@example.de
Telefon: +49 123 456789

Ich bitte um schnellstmögliche Bearbeitung meines Antrags.

Mit freundlichen Grüßen,
Max Mustermann"""

    # Save to temp file
    with open('/tmp/test_loan_application.txt', 'w') as f:
        f.write(test_doc_content)

    # Upload document
    try:
        with open('/tmp/test_loan_application.txt', 'rb') as f:
            files = {'file': ('loan_application.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/process-document", files=files)

        if response.status_code == 200:
            result = response.json()
            print("✅ Document processed successfully!")
            print(f"\n📊 Results:")
            print(f"  Document ID: {result.get('document_id')}")
            print(f"  Category: {result.get('category')}")
            print(f"  Urgency: {result.get('urgency')}")
            print(f"  Department: {result.get('department')}")
            print(f"  Requires Immediate Attention: {result.get('requires_immediate_attention')}")
            print(f"  Confidence Score: {result.get('confidence_score')}")
            print(f"\n  Extracted Info:")
            for key, value in result.get('extracted_info', {}).items():
                print(f"    {key}: {value}")
            print(f"\n  Metadata:")
            for key, value in result.get('metadata', {}).items():
                print(f"    {key}: {value}")

            return result.get('document_id')
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        return None

def test_search(query="Darlehen"):
    """Test semantic search"""
    print(f"\n🔎 Testing semantic search for: '{query}'...")
    try:
        response = requests.get(f"{BASE_URL}/search-documents", params={"query": query, "n_results": 3})
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Found {len(results.get('results', []))} similar documents")
            for i, result in enumerate(results.get('results', []), 1):
                print(f"\n  Result {i}:")
                print(f"    Document ID: {result.get('document_id')}")
                print(f"    Similarity: {result.get('similarity', 0):.2%}")
                print(f"    Preview: {result.get('text_preview', '')[:100]}...")
        else:
            print(f"❌ Search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error during search: {e}")

def test_get_document(document_id):
    """Test retrieving a specific document"""
    if not document_id:
        print("\n⚠️  Skipping document retrieval test (no document ID)")
        return

    print(f"\n📖 Testing document retrieval...")
    try:
        response = requests.get(f"{BASE_URL}/document/{document_id}")
        if response.status_code == 200:
            doc = response.json()
            print(f"✅ Successfully retrieved document: {document_id}")
            print(f"   Preview: {doc.get('document', '')[:100]}...")
        else:
            print(f"❌ Failed to retrieve document: {response.status_code}")
    except Exception as e:
        print(f"❌ Error retrieving document: {e}")

def main():
    print("=" * 60)
    print("🧪 Bank Document Classification System - Workflow Test")
    print("=" * 60)

    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Server is not running. Please start with: docker compose up -d")
        return

    # Test 2: Process document
    document_id = test_document_processing()

    # Wait a bit for background processing
    time.sleep(2)

    # Test 3: Search documents
    test_search("Kredit Darlehen")

    # Test 4: Retrieve specific document
    test_get_document(document_id)

    print("\n" + "=" * 60)
    print("✅ Workflow test completed!")
    print("=" * 60)
    print(f"\n📚 Access API documentation at: {BASE_URL}/docs")

if __name__ == "__main__":
    main()

