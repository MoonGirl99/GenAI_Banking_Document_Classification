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

