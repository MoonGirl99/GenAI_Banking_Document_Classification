"""
Unit tests for embedding service
"""
import pytest
from unittest.mock import Mock, patch
from app.services.embedding_service import EmbeddingService


@pytest.mark.unit
class TestEmbeddingService:
    """Test EmbeddingService class"""

    @patch('app.services.embedding_service.Mistral')
    def test_service_initialization(self, mock_mistral_class, mock_env_vars):
        """Test embedding service initializes correctly"""
        service = EmbeddingService()
        assert service.client is not None
        mock_mistral_class.assert_called_once()

    @patch('app.services.embedding_service.Mistral')
    def test_generate_embedding_success(self, mock_mistral_class, mock_mistral_client):
        """Test successful embedding generation"""
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()
        result = service.generate_embedding("Test text")

        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)
        mock_mistral_client.embeddings.create.assert_called_once()

    @patch('app.services.embedding_service.Mistral')
    def test_generate_embedding_with_different_texts(self, mock_mistral_class, mock_mistral_client):
        """Test embedding generation with different input texts"""
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()

        texts = [
            "Short text",
            "This is a longer text with more words and details",
            "German text: Sehr geehrte Damen und Herren"
        ]

        for text in texts:
            result = service.generate_embedding(text)
            assert isinstance(result, list)
            assert len(result) > 0

    @patch('app.services.embedding_service.Mistral')
    def test_generate_embedding_empty_text(self, mock_mistral_class, mock_mistral_client):
        """Test embedding generation with empty text"""
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()
        result = service.generate_embedding("")

        assert isinstance(result, list)

    @patch('app.services.embedding_service.Mistral')
    def test_generate_embedding_api_error(self, mock_mistral_class):
        """Test handling of API errors"""
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_mistral_class.return_value = mock_client

        service = EmbeddingService()

        with pytest.raises(Exception) as exc_info:
            service.generate_embedding("Test text")

        assert "Embedding generation failed" in str(exc_info.value)

    @patch('app.services.embedding_service.Mistral')
    def test_generate_batch_embeddings_success(self, mock_mistral_class, mock_mistral_client):
        """Test successful batch embedding generation"""
        # Mock multiple embeddings
        mock_mistral_client.embeddings.create.return_value = Mock(
            data=[
                Mock(embedding=[0.1] * 1024),
                Mock(embedding=[0.2] * 1024),
                Mock(embedding=[0.3] * 1024)
            ]
        )
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()
        texts = ["Text 1", "Text 2", "Text 3"]
        results = service.generate_batch_embeddings(texts)

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(emb, list) for emb in results)
        assert all(len(emb) == 1024 for emb in results)

    @patch('app.services.embedding_service.Mistral')
    def test_generate_batch_embeddings_single_text(self, mock_mistral_class, mock_mistral_client):
        """Test batch embedding with single text"""
        mock_mistral_client.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1024)]
        )
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()
        results = service.generate_batch_embeddings(["Single text"])

        assert len(results) == 1
        assert isinstance(results[0], list)

    @patch('app.services.embedding_service.Mistral')
    def test_generate_batch_embeddings_empty_list(self, mock_mistral_class, mock_mistral_client):
        """Test batch embedding with empty list"""
        mock_mistral_client.embeddings.create.return_value = Mock(data=[])
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()
        results = service.generate_batch_embeddings([])

        assert isinstance(results, list)
        assert len(results) == 0

    @patch('app.services.embedding_service.Mistral')
    def test_generate_batch_embeddings_api_error(self, mock_mistral_class):
        """Test batch embedding handling of API errors"""
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("Batch API Error")
        mock_mistral_class.return_value = mock_client

        service = EmbeddingService()

        with pytest.raises(Exception) as exc_info:
            service.generate_batch_embeddings(["Text 1", "Text 2"])

        assert "Batch embedding generation failed" in str(exc_info.value)

    @patch('app.services.embedding_service.Mistral')
    def test_embedding_vector_dimensions(self, mock_mistral_class, mock_mistral_client):
        """Test that embedding vectors have consistent dimensions"""
        mock_mistral_class.return_value = mock_mistral_client

        service = EmbeddingService()

        # Generate multiple embeddings
        embedding1 = service.generate_embedding("First text")
        embedding2 = service.generate_embedding("Second text")

        assert len(embedding1) == len(embedding2)
        assert len(embedding1) == 1024
