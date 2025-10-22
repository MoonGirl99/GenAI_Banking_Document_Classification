"""
Unit tests for document models
"""
import pytest
from datetime import datetime
from app.models.document import (
    DocumentCategory,
    UrgencyLevel,
    DocumentMetadata,
    ProcessedDocument
)


class TestDocumentCategory:
    """Test DocumentCategory enum"""

    def test_category_values(self):
        """Test all category enum values are valid"""
        assert DocumentCategory.LOAN_APPLICATION.value == "loan_applications"
        assert DocumentCategory.ACCOUNT_INQUIRY.value == "account_inquiries"
        assert DocumentCategory.COMPLAINT.value == "complaints"
        assert DocumentCategory.KYC_UPDATE.value == "kyc_updates"
        assert DocumentCategory.GENERAL.value == "general_correspondence"

    def test_category_from_string(self):
        """Test creating category from string"""
        category = DocumentCategory("loan_applications")
        assert category == DocumentCategory.LOAN_APPLICATION


class TestUrgencyLevel:
    """Test UrgencyLevel enum"""

    def test_urgency_values(self):
        """Test all urgency enum values are valid"""
        assert UrgencyLevel.HIGH.value == "high"
        assert UrgencyLevel.MEDIUM.value == "medium"
        assert UrgencyLevel.LOW.value == "low"

    def test_urgency_from_string(self):
        """Test creating urgency from string"""
        urgency = UrgencyLevel("high")
        assert urgency == UrgencyLevel.HIGH


class TestDocumentMetadata:
    """Test DocumentMetadata model"""

    def test_metadata_creation_full(self):
        """Test creating metadata with all fields"""
        metadata = DocumentMetadata(
            customer_id="CUST-123",
            account_number="DE1234567890",
            email="test@example.com",
            phone="+49123456789",
            subject="Test Subject",
            language="de"
        )
        assert metadata.customer_id == "CUST-123"
        assert metadata.account_number == "DE1234567890"
        assert metadata.email == "test@example.com"
        assert metadata.phone == "+49123456789"
        assert metadata.subject == "Test Subject"
        assert metadata.language == "de"

    def test_metadata_creation_minimal(self):
        """Test creating metadata with minimal fields"""
        metadata = DocumentMetadata()
        assert metadata.customer_id is None
        assert metadata.account_number is None
        assert metadata.email is None
        assert metadata.phone is None
        assert metadata.subject is None
        assert metadata.language == "de"  # Default value

    def test_metadata_optional_fields(self):
        """Test metadata with some optional fields"""
        metadata = DocumentMetadata(
            customer_id="CUST-456",
            email="customer@example.com"
        )
        assert metadata.customer_id == "CUST-456"
        assert metadata.email == "customer@example.com"
        assert metadata.account_number is None


class TestProcessedDocument:
    """Test ProcessedDocument model"""

    def test_document_creation_complete(self, sample_metadata):
        """Test creating a complete processed document"""
        doc = ProcessedDocument(
            raw_text="Test document text",
            category=DocumentCategory.LOAN_APPLICATION,
            urgency_level=UrgencyLevel.HIGH,
            metadata=sample_metadata,
            extracted_info={"key": "value"},
            confidence_score=0.95,
            assigned_department="Loans",
            requires_immediate_attention=True
        )

        assert doc.raw_text == "Test document text"
        assert doc.category == DocumentCategory.LOAN_APPLICATION
        assert doc.urgency_level == UrgencyLevel.HIGH
        assert doc.confidence_score == 0.95
        assert doc.assigned_department == "Loans"
        assert doc.requires_immediate_attention is True
        assert isinstance(doc.id, str)
        assert len(doc.id) > 0
        assert isinstance(doc.processed_at, datetime)

    def test_document_auto_generated_id(self):
        """Test that document ID is auto-generated"""
        doc1 = ProcessedDocument(
            raw_text="Doc 1",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.5,
            assigned_department="General"
        )

        doc2 = ProcessedDocument(
            raw_text="Doc 2",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.5,
            assigned_department="General"
        )

        assert doc1.id != doc2.id
        assert len(doc1.id) > 0
        assert len(doc2.id) > 0

    def test_document_auto_timestamp(self):
        """Test that timestamp is auto-generated"""
        doc = ProcessedDocument(
            raw_text="Test",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.5,
            assigned_department="General"
        )

        assert isinstance(doc.processed_at, datetime)
        assert doc.processed_at <= datetime.now()

    def test_document_with_embedding(self):
        """Test document with embedding vector"""
        embedding = [0.1, 0.2, 0.3] * 100
        doc = ProcessedDocument(
            raw_text="Test",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.5,
            assigned_department="General",
            embedding=embedding
        )

        assert doc.embedding == embedding
        assert len(doc.embedding) == 300

    def test_document_default_values(self):
        """Test document default values"""
        doc = ProcessedDocument(
            raw_text="Test",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.5,
            assigned_department="General"
        )

        assert doc.embedding is None
        assert doc.requires_immediate_attention is False

    def test_confidence_score_range(self):
        """Test confidence score validation"""
        # Valid confidence scores
        doc = ProcessedDocument(
            raw_text="Test",
            category=DocumentCategory.GENERAL,
            urgency_level=UrgencyLevel.LOW,
            metadata=DocumentMetadata(),
            extracted_info={},
            confidence_score=0.95,
            assigned_department="General"
        )
        assert doc.confidence_score == 0.95

    def test_extracted_info_structure(self):
        """Test extracted info dictionary structure"""
        extracted = {
            "required_action": "Review application",
            "key_points": ["Point 1", "Point 2"],
            "mentioned_amounts": "5000 EUR",
            "reference_numbers": ["REF-001"]
        }

        doc = ProcessedDocument(
            raw_text="Test",
            category=DocumentCategory.LOAN_APPLICATION,
            urgency_level=UrgencyLevel.MEDIUM,
            metadata=DocumentMetadata(),
            extracted_info=extracted,
            confidence_score=0.9,
            assigned_department="Loans"
        )

        assert doc.extracted_info["required_action"] == "Review application"
        assert len(doc.extracted_info["key_points"]) == 2
        assert doc.extracted_info["mentioned_amounts"] == "5000 EUR"

