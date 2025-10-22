"""
API integration tests
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app
import json


@pytest.mark.api
class TestDocumentProcessingAPI:
    """Test document processing API endpoints"""

    @patch('app.main.ocr_service')
    @patch('app.main.llm_service')
    @patch('app.main.embedding_service')
    @patch('app.main.db_client')
    def test_process_document_file_upload(
        self, mock_db, mock_embedding, mock_llm, mock_ocr
    ):
        """Test processing document via file upload"""
        # Setup mocks
        mock_ocr.process_document.return_value = Mock(raw_text="Sample text")
        mock_llm.classify_and_extract.return_value = Mock(
            id="doc-123",
            category="loan_applications",
            urgency_level="medium",
            metadata=Mock(
                customer_id="CUST-123",
                account_number="DE123",
                email=None,
                phone=None
            ),
            extracted_info={},
            confidence_score=0.9,
            assigned_department="Loans",
            requires_immediate_attention=False
        )
        mock_embedding.generate_embedding.return_value = [0.1] * 1024

        client = TestClient(app)

        # Create test file
        files = {"file": ("test.txt", b"Test document content", "text/plain")}
        response = client.post("/process-document", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "category" in data

    @patch('app.main.llm_service')
    @patch('app.main.embedding_service')
    @patch('app.main.db_client')
    def test_process_text_input(self, mock_db, mock_embedding, mock_llm):
        """Test processing text via direct input"""
        # Setup mocks
        mock_llm.classify_and_extract.return_value = Mock(
            id="doc-456",
            category="general_correspondence",
            urgency_level="low",
            metadata=Mock(
                customer_id=None,
                account_number=None,
                email=None,
                phone=None
            ),
            extracted_info={},
            confidence_score=0.8,
            assigned_department="General",
            requires_immediate_attention=False
        )
        mock_embedding.generate_embedding.return_value = [0.2] * 1024

        client = TestClient(app)

        payload = {
            "text": "This is a test document text",
            "filename": "test.txt"
        }
        response = client.post("/process-text", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["category"] == "general_correspondence"

    def test_process_text_empty_input(self):
        """Test processing empty text returns error"""
        client = TestClient(app)

        payload = {"text": "", "filename": "empty.txt"}
        response = client.post("/process-text", json=payload)

        assert response.status_code == 400

    def test_health_check(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_home_endpoint(self):
        """Test home endpoint returns HTML"""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @patch('app.main.embedding_service')
    @patch('app.main.db_client')
    def test_search_documents(self, mock_db, mock_embedding):
        """Test search documents endpoint"""
        mock_embedding.generate_embedding.return_value = [0.1] * 1024
        mock_db.search_similar_documents.return_value = {
            "ids": ["doc-1"],
            "distances": [0.1],
            "documents": ["Sample document"],
            "metadatas": [{"category": "loan_applications"}]
        }

        client = TestClient(app)
        response = client.get("/search-documents?query=loan&n_results=5")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @patch('app.main.db_client')
    def test_get_document_by_id(self, mock_db):
        """Test retrieving specific document"""
        mock_db.get_document_by_id.return_value = {
            "id": "doc-123",
            "document": "Sample text",
            "metadata": {"category": "loan_applications"}
        }

        client = TestClient(app)
        response = client.get("/document/doc-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc-123"

    @patch('app.main.db_client')
    def test_get_nonexistent_document(self, mock_db):
        """Test retrieving non-existent document"""
        mock_db.get_document_by_id.return_value = None

        client = TestClient(app)
        response = client.get("/document/nonexistent")

        assert response.status_code == 404

    @patch('app.main.db_client')
    def test_get_documents_by_category(self, mock_db):
        """Test getting documents grouped by category"""
        mock_db.collection.get.return_value = {
            "ids": ["doc-1", "doc-2"],
            "metadatas": [
                {"category": "loan_applications", "filename": "loan.txt", "urgency": "medium", "processed_at": "2024-01-01"},
                {"category": "complaints", "filename": "complaint.txt", "urgency": "high", "processed_at": "2024-01-02"}
            ],
            "documents": ["Doc 1", "Doc 2"]
        }

        client = TestClient(app)
        response = client.get("/documents-by-category")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data

    @patch('app.main.llm_service')
    @patch('app.main.embedding_service')
    @patch('app.main.db_client')
    def test_chat_endpoint(self, mock_db, mock_embedding, mock_llm):
        """Test chat endpoint"""
        mock_embedding.generate_embedding.return_value = [0.1] * 1024
        mock_db.search_similar_documents.return_value = {
            "ids": [], "distances": [], "documents": [], "metadatas": []
        }
        mock_llm.chat_with_context.return_value = "This is a helpful response"

        client = TestClient(app)
        payload = {
            "query": "What documents do we have?",
            "chat_history": []
        }
        response = client.post("/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_endpoint_missing_query(self):
        """Test chat endpoint with missing query"""
        client = TestClient(app)
        payload = {"chat_history": []}
        response = client.post("/chat", json=payload)

        assert response.status_code == 400


@pytest.mark.api
class TestAdminEndpoints:
    """Test admin endpoints"""

    @patch('app.main.db_client')
    def test_collection_stats(self, mock_db):
        """Test collection statistics endpoint"""
        mock_db.collection.name = "bank_documents"
        mock_db.collection.count.return_value = 42

        client = TestClient(app)
        response = client.get("/api/admin/collection-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["collection"] == "bank_documents"
        assert data["count"] == 42

    @patch('app.main.db_client')
    def test_peek_documents(self, mock_db):
        """Test peek endpoint"""
        mock_db.collection.get.return_value = {
            "ids": ["doc-1"],
            "documents": ["Sample"],
            "metadatas": [{"category": "general"}]
        }

        client = TestClient(app)
        response = client.get("/api/admin/peek?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
"""
Unit tests for routing service
"""
import pytest
from unittest.mock import Mock, patch
from app.services.routing_service import RoutingService
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata


@pytest.mark.unit
class TestRoutingService:
    """Test RoutingService class"""

    def test_service_initialization(self):
        """Test routing service initializes correctly"""
        service = RoutingService()
        assert service is not None

    def test_route_document_loan_application(self, sample_processed_document):
        """Test routing loan application"""
        service = RoutingService()

        # Create loan application document
        doc = ProcessedDocument(
            raw_text="Loan application",
            category=DocumentCategory.LOAN_APPLICATION,
            urgency_level=UrgencyLevel.MEDIUM,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.9,
            assigned_department="Loans"
        )

        result = service.route_document(doc)

        assert result is not None
        assert "loans@bank.de" in result["email"].lower() or result["department"] == "Loans"

    def test_route_document_complaint(self):
        """Test routing complaint"""
        service = RoutingService()

        doc = ProcessedDocument(
            raw_text="Complaint text",
            category=DocumentCategory.COMPLAINT,
            urgency_level=UrgencyLevel.HIGH,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.95,
            assigned_department="Complaints",
            requires_immediate_attention=True
        )

        result = service.route_document(doc)

        assert result is not None
        assert result.get("priority") == "HIGH" or result.get("urgent") is True

    def test_route_high_urgency_document(self):
        """Test routing high urgency documents"""
        service = RoutingService()

        doc = ProcessedDocument(
            raw_text="Urgent matter",
            category=DocumentCategory.ACCOUNT_INQUIRY,
            urgency_level=UrgencyLevel.HIGH,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.88,
            assigned_department="Accounts",
            requires_immediate_attention=True
        )

        result = service.route_document(doc)

        assert result is not None

    def test_route_kyc_update(self):
        """Test routing KYC update"""
        service = RoutingService()

        doc = ProcessedDocument(
            raw_text="KYC update",
            category=DocumentCategory.KYC_UPDATE,
            urgency_level=UrgencyLevel.MEDIUM,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.92,
            assigned_department="Compliance"
        )

        result = service.route_document(doc)

        assert result is not None
        assert "compliance" in result["department"].lower() or "compliance@bank.de" in result.get("email", "").lower()

    def test_route_general_correspondence(self):
        """Test routing general correspondence"""
        service = RoutingService()

        doc = ProcessedDocument(
            raw_text="General inquiry",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.7,
            assigned_department="General"
        )

        result = service.route_document(doc)

        assert result is not None

    def test_get_department_email(self):
        """Test getting department email addresses"""
        service = RoutingService()

        # Test each category has an email
        categories = [
            DocumentCategory.LOAN_APPLICATION,
            DocumentCategory.ACCOUNT_INQUIRY,
            DocumentCategory.COMPLAINT,
            DocumentCategory.KYC_UPDATE,
            DocumentCategory.GENERAL
        ]

        for category in categories:
            email = service.get_department_email(category.value)
            assert email is not None
            assert "@" in email

    def test_priority_assignment_high(self):
        """Test priority assignment for high urgency"""
        service = RoutingService()
        priority = service.assign_priority(UrgencyLevel.HIGH)

        assert priority in ["HIGH", "URGENT", "IMMEDIATE"]

    def test_priority_assignment_medium(self):
        """Test priority assignment for medium urgency"""
        service = RoutingService()
        priority = service.assign_priority(UrgencyLevel.MEDIUM)

        assert priority in ["MEDIUM", "NORMAL"]

    def test_priority_assignment_low(self):
        """Test priority assignment for low urgency"""
        service = RoutingService()
        priority = service.assign_priority(UrgencyLevel.LOW)

        assert priority in ["LOW", "ROUTINE"]

