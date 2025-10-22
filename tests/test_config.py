"""
Test configuration and settings
"""
import pytest
from unittest.mock import patch
from app.config import Settings


@pytest.mark.unit
class TestConfiguration:
    """Test application configuration"""

    def test_default_settings(self, mock_env_vars):
        """Test default configuration values"""
        settings = Settings()

        assert settings.MISTRAL_MODEL == "ministral-8b-2410"
        assert settings.MISTRAL_EMBEDDING_MODEL == "mistral-embed"
        assert settings.CHROMA_HOST == "localhost"
        assert settings.CHROMA_PORT == 8000
        assert settings.CHROMA_COLLECTION_NAME == "bank_documents"

    def test_department_emails_configured(self, mock_env_vars):
        """Test department email configuration"""
        settings = Settings()

        assert "loan_applications" in settings.DEPARTMENT_EMAILS
        assert "complaints" in settings.DEPARTMENT_EMAILS
        assert "account_inquiries" in settings.DEPARTMENT_EMAILS
        assert "kyc_updates" in settings.DEPARTMENT_EMAILS
        assert "general_correspondence" in settings.DEPARTMENT_EMAILS

        # Verify all emails are valid format
        for email in settings.DEPARTMENT_EMAILS.values():
            assert "@" in email
            assert "." in email

    def test_urgency_keywords_configured(self, mock_env_vars):
        """Test urgency keywords are configured"""
        settings = Settings()

        assert len(settings.HIGH_URGENCY_KEYWORDS) > 0
        assert "urgent" in settings.HIGH_URGENCY_KEYWORDS
        assert "dringend" in settings.HIGH_URGENCY_KEYWORDS

    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'custom-key', 'CHROMA_PORT': '9000'})
    def test_environment_override(self):
        """Test environment variables override defaults"""
        settings = Settings()

        assert settings.MISTRAL_API_KEY == 'custom-key'
        assert settings.CHROMA_PORT == 9000

    def test_api_key_required(self):
        """Test that API key is required"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(Exception):
                Settings()
