"""
Pytest configuration and shared fixtures
"""
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata


@pytest.fixture
def sample_text():
    """Sample document text for testing"""
    return """
    Sehr geehrte Damen und Herren,
    
    ich möchte einen Kredit über 50.000 Euro beantragen.
    Meine Kundennummer ist: CUST-12345
    Kontonummer: DE89370400440532013000
    Email: max.mustermann@email.de
    Telefon: +49 123 456789
    
    Bitte kontaktieren Sie mich schnellstmöglich.
    
    Mit freundlichen Grüßen,
    Max Mustermann
    """


@pytest.fixture
def sample_complaint_text():
    """Sample complaint text for testing"""
    return """
    URGENT COMPLAINT
    
    Customer ID: CUST-99999
    Account: DE89370400440532013001
    
    I am extremely dissatisfied with the unauthorized charges on my account.
    This is unacceptable and requires immediate attention.
    
    Please resolve this issue ASAP.
    
    Contact: complaint@email.com
    Phone: +49 987 654321
    """


@pytest.fixture
def sample_metadata():
    """Sample document metadata"""
    return DocumentMetadata(
        customer_id="CUST-12345",
        account_number="DE89370400440532013000",
        email="max.mustermann@email.de",
        phone="+49 123 456789",
        subject="Loan Application"
    )


@pytest.fixture
def sample_processed_document(sample_text, sample_metadata):
    """Sample processed document"""
    return ProcessedDocument(
        raw_text=sample_text,
        category=DocumentCategory.LOAN_APPLICATION,
        urgency_level=UrgencyLevel.MEDIUM,
        metadata=sample_metadata,
        extracted_info={
            "required_action": "Process loan application",
            "key_points": ["Loan amount: 50,000 EUR", "Customer contact requested"],
            "mentioned_amounts": "50,000 EUR",
            "reference_numbers": ["CUST-12345", "DE89370400440532013000"]
        },
        confidence_score=0.95,
        assigned_department="Loans Department",
        requires_immediate_attention=False
    )


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral API client"""
    mock = Mock()

    # Mock embedding response
    mock.embeddings.create.return_value = Mock(
        data=[Mock(embedding=[0.1] * 1024)]
    )

    # Mock chat completion response
    mock.chat.complete.return_value = Mock(
        choices=[Mock(
            message=Mock(
                content='{"category": "loan_applications", "urgency": "medium", "metadata": {"customer_id": "CUST-12345", "account_number": "DE89370400440532013000", "email": "max.mustermann@email.de", "phone": "+49 123 456789", "subject": "Loan Application"}, "extracted_info": {"required_action": "Process loan application", "key_points": ["Loan amount: 50,000 EUR"], "mentioned_amounts": "50,000 EUR", "reference_numbers": ["CUST-12345"]}, "confidence_score": 0.95}'
            )
        )]
    )

    return mock


@pytest.fixture
def mock_chromadb_collection():
    """Mock ChromaDB collection"""
    mock = Mock()
    mock.name = "bank_documents"
    mock.count.return_value = 0
    mock.add.return_value = None
    mock.query.return_value = {
        "ids": [["doc-1"]],
        "distances": [[0.1]],
        "documents": [["Sample document"]],
        "metadatas": [[{"category": "loan_applications"}]]
    }
    mock.get.return_value = {
        "ids": ["doc-1"],
        "documents": ["Sample document"],
        "metadatas": [{"category": "loan_applications"}],
        "embeddings": [[0.1] * 1024]
    }
    return mock


@pytest.fixture
def test_client():
    """FastAPI test client"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing"""
    monkeypatch.setenv("MISTRAL_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("MISTRAL_MODEL", "ministral-8b-2410")
    monkeypatch.setenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")
    monkeypatch.setenv("CHROMA_HOST", "localhost")
    monkeypatch.setenv("CHROMA_PORT", "8000")
