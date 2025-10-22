"""
Unit tests for LLM service
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.llm_service import LLMService
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument
import json


@pytest.mark.unit
class TestLLMService:
    """Test LLMService class"""

    @patch('app.services.llm_service.Mistral')
    def test_service_initialization(self, mock_mistral_class, mock_env_vars):
        """Test LLM service initializes correctly"""
        service = LLMService()
        assert service.client is not None
        mock_mistral_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_and_extract_success(self, mock_mistral_class, mock_mistral_client, sample_text):
        """Test successful document classification"""
        mock_mistral_class.return_value = mock_mistral_client

        service = LLMService()
        result = await service.classify_and_extract(sample_text)

        assert isinstance(result, ProcessedDocument)
        assert result.category == DocumentCategory.LOAN_APPLICATION
        assert result.urgency_level == UrgencyLevel.MEDIUM
        assert result.metadata.customer_id == "CUST-12345"
        assert result.confidence_score == 0.95
        assert result.assigned_department is not None

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_complaint_urgent(self, mock_mistral_class, sample_complaint_text):
        """Test classification of urgent complaint"""
        mock_client = Mock()
        mock_client.chat.complete.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    content=json.dumps({
                        "category": "complaints",
                        "urgency": "high",
                        "metadata": {
                            "customer_id": "CUST-99999",
                            "account_number": "DE89370400440532013001",
                            "email": "complaint@email.com",
                            "phone": "+49 987 654321",
                            "subject": "Urgent Complaint"
                        },
                        "extracted_info": {
                            "required_action": "Investigate unauthorized charges",
                            "key_points": ["Unauthorized charges", "Immediate attention required"],
                            "mentioned_amounts": None,
                            "reference_numbers": ["CUST-99999"]
                        },
                        "confidence_score": 0.98
                    })
                )
            )]
        )
        mock_mistral_class.return_value = mock_client

        service = LLMService()
        result = await service.classify_and_extract(sample_complaint_text)

        assert result.category == DocumentCategory.COMPLAINT
        assert result.urgency_level == UrgencyLevel.HIGH
        assert result.requires_immediate_attention is True
        assert result.confidence_score == 0.98

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_with_retry_on_rate_limit(self, mock_mistral_class):
        """Test retry logic on rate limit error"""
        mock_client = Mock()
        # First call fails with 429, second succeeds
        mock_client.chat.complete.side_effect = [
            Exception("429 Rate Limited"),
            Mock(
                choices=[Mock(
                    message=Mock(
                        content=json.dumps({
                            "category": "general_correspondence",
                            "urgency": "low",
                            "metadata": {"customer_id": None, "account_number": None, "email": None, "phone": None,
                                         "subject": None},
                            "extracted_info": {"required_action": "File", "key_points": [], "mentioned_amounts": None,
                                               "reference_numbers": []},
                            "confidence_score": 0.7
                        })
                    )
                )]
            )
        ]
        mock_mistral_class.return_value = mock_client

        service = LLMService()

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = await service.classify_and_extract("Test text")

        assert isinstance(result, ProcessedDocument)
        assert mock_client.chat.complete.call_count == 2

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_max_retries_exceeded(self, mock_mistral_class):
        """Test failure after max retries"""
        mock_client = Mock()
        mock_client.chat.complete.side_effect = Exception("429 Rate Limited")
        mock_mistral_class.return_value = mock_client

        service = LLMService()

        with patch('time.sleep'):
            with pytest.raises(Exception) as exc_info:
                await service.classify_and_extract("Test text")

        assert "LLM classification failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_invalid_json_response(self, mock_mistral_class):
        """Test handling of invalid JSON response"""
        mock_client = Mock()
        mock_client.chat.complete.return_value = Mock(
            choices=[Mock(message=Mock(content="Invalid JSON"))]
        )
        mock_mistral_class.return_value = mock_client

        service = LLMService()

        with pytest.raises(Exception):
            await service.classify_and_extract("Test text")

    def test_get_system_prompt(self):
        """Test system prompt generation"""
        service = LLMService()
        prompt = service._get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "German" in prompt or "banking" in prompt
        assert "JSON" in prompt

    def test_get_department_mapping(self):
        """Test department assignment logic"""
        service = LLMService()

        # Test each category maps to a department
        assert service._get_department("loan_applications") is not None
        assert service._get_department("complaints") is not None
        assert service._get_department("account_inquiries") is not None
        assert service._get_department("kyc_updates") is not None
        assert service._get_department("general_correspondence") is not None

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_extracts_customer_info(self, mock_mistral_class, mock_mistral_client):
        """Test that customer information is properly extracted"""
        mock_mistral_class.return_value = mock_mistral_client

        service = LLMService()
        text = """
        Customer ID: CUST-12345
        Account: DE1234567890
        Email: customer@bank.de
        Phone: +49 123 456789
        """

        result = await service.classify_and_extract(text)

        assert result.metadata.customer_id is not None
        assert result.metadata.account_number is not None
        assert result.metadata.email is not None
        assert result.metadata.phone is not None

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_classify_handles_missing_metadata(self, mock_mistral_class):
        """Test handling of documents with missing metadata"""
        mock_client = Mock()
        mock_client.chat.complete.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    content=json.dumps({
                        "category": "general_correspondence",
                        "urgency": "low",
                        "metadata": {
                            "customer_id": None,
                            "account_number": None,
                            "email": None,
                            "phone": None,
                            "subject": "General Inquiry"
                        },
                        "extracted_info": {
                            "required_action": "Review and respond",
                            "key_points": ["General question"],
                            "mentioned_amounts": None,
                            "reference_numbers": []
                        },
                        "confidence_score": 0.6
                    })
                )
            )]
        )
        mock_mistral_class.return_value = mock_client

        service = LLMService()
        result = await service.classify_and_extract("Generic text")

        assert result.metadata.customer_id is None
        assert result.metadata.account_number is None
        assert result.category == DocumentCategory.GENERAL

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_chat_with_context(self, mock_mistral_class, mock_mistral_client):
        """Test chat functionality with context"""
        mock_mistral_class.return_value = mock_mistral_client
        mock_mistral_client.chat.complete.return_value = Mock(
            choices=[Mock(message=Mock(content="This is a helpful response about the document."))]
        )

        service = LLMService()
        response = await service.chat_with_context(
            query="What is this document about?",
            context="Document about loan application",
            chat_history=[]
        )

        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    @patch('app.services.llm_service.Mistral')
    async def test_chat_with_history(self, mock_mistral_class, mock_mistral_client):
        """Test chat with conversation history"""
        mock_mistral_class.return_value = mock_mistral_client
        mock_mistral_client.chat.complete.return_value = Mock(
            choices=[Mock(message=Mock(content="Follow-up response"))]
        )

        service = LLMService()
        chat_history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"}
        ]

        response = await service.chat_with_context(
            query="Follow-up question",
            context="Context",
            chat_history=chat_history
        )

        assert isinstance(response, str)
        mock_mistral_client.chat.complete.assert_called_once()

