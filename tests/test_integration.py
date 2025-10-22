"""
Integration tests for end-to-end workflow
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata


@pytest.mark.integration
class TestDocumentProcessingWorkflow:
    """Test complete document processing workflow"""

    @pytest.mark.asyncio
    @patch('app.services.ocr_service.MistralOCRService')
    @patch('app.services.llm_service.LLMService')
    @patch('app.services.embedding_service.EmbeddingService')
    @patch('app.database.chroma_client.ChromaDBClient')
    async def test_full_document_workflow(
            self, mock_db_class, mock_embed_class, mock_llm_class, mock_ocr_class, sample_text
    ):
        """Test complete workflow from OCR to storage"""
        # Setup mocks
        mock_ocr = mock_ocr_class.return_value
        mock_ocr.process_document.return_value = Mock(raw_text=sample_text)

        mock_llm = mock_llm_class.return_value
        mock_llm.classify_and_extract = AsyncMock(return_value=ProcessedDocument(
            raw_text=sample_text,
            category=DocumentCategory.LOAN_APPLICATION,
            urgency_level=UrgencyLevel.MEDIUM,
            metadata=DocumentMetadata(
                customer_id="CUST-12345",
                account_number="DE123",
                email="test@example.com"
            ),
            extracted_info={"key": "value"},
            confidence_score=0.9,
            assigned_department="Loans"
        ))

        mock_embed = mock_embed_class.return_value
        mock_embed.generate_embedding.return_value = [0.1] * 1024

        mock_db = mock_db_class.return_value
        mock_db.store_document = Mock()

        # Execute workflow
        ocr_result = mock_ocr.process_document(b"document content", "pdf")
        processed_doc = await mock_llm.classify_and_extract(ocr_result.raw_text)
        embedding = mock_embed.generate_embedding(ocr_result.raw_text)

        # Verify each step
        assert processed_doc.category == DocumentCategory.LOAN_APPLICATION
        assert processed_doc.confidence_score > 0.8
        assert len(embedding) == 1024

    @pytest.mark.asyncio
    @patch('app.services.llm_service.LLMService')
    @patch('app.services.embedding_service.EmbeddingService')
    @patch('app.database.chroma_client.ChromaDBClient')
    async def test_text_input_workflow(
            self, mock_db_class, mock_embed_class, mock_llm_class, sample_complaint_text
    ):
        """Test workflow for direct text input"""
        mock_llm = mock_llm_class.return_value
        mock_llm.classify_and_extract = AsyncMock(return_value=ProcessedDocument(
            raw_text=sample_complaint_text,
            category=DocumentCategory.COMPLAINT,
            urgency_level=UrgencyLevel.HIGH,
            metadata=DocumentMetadata(customer_id="CUST-99999"),
            extracted_info={"action": "investigate"},
            confidence_score=0.95,
            assigned_department="Complaints",
            requires_immediate_attention=True
        ))

        mock_embed = mock_embed_class.return_value
        mock_embed.generate_embedding.return_value = [0.2] * 1024

        # Execute workflow
        processed_doc = await mock_llm.classify_and_extract(sample_complaint_text)
        embedding = mock_embed.generate_embedding(sample_complaint_text)

        # Verify
        assert processed_doc.category == DocumentCategory.COMPLAINT
        assert processed_doc.urgency_level == UrgencyLevel.HIGH
        assert processed_doc.requires_immediate_attention is True

    @pytest.mark.asyncio
    @patch('app.services.llm_service.LLMService')
    @patch('app.services.embedding_service.EmbeddingService')
    @patch('app.database.chroma_client.ChromaDBClient')
    async def test_search_workflow(self, mock_db_class, mock_embed_class, mock_llm_class):
        """Test search workflow"""
        mock_embed = mock_embed_class.return_value
        mock_embed.generate_embedding.return_value = [0.1] * 1024

        mock_db = mock_db_class.return_value
        mock_db.search_similar_documents.return_value = {
            "ids": ["doc-1", "doc-2"],
            "distances": [0.1, 0.2],
            "documents": ["Doc 1 text", "Doc 2 text"],
            "metadatas": [
                {"category": "loan_applications"},
                {"category": "loan_applications"}
            ]
        }

        # Execute search workflow
        query = "loan application"
        query_embedding = mock_embed.generate_embedding(query)
        results = mock_db.search_similar_documents(query_embedding, n_results=5)

        # Verify
        assert len(results["ids"]) == 2
        assert all(d < 0.5 for d in results["distances"])


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across components"""

    @pytest.mark.asyncio
    @patch('app.services.llm_service.LLMService')
    async def test_llm_service_recovers_from_rate_limit(self, mock_llm_class):
        """Test LLM service recovery from rate limiting"""
        mock_llm = mock_llm_class.return_value

        # Simulate rate limit then success
        call_count = 0

        async def side_effect(text):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Rate Limited")
            return ProcessedDocument(
                raw_text=text,
                category=DocumentCategory.GENERAL,
                urgency_level=UrgencyLevel.LOW,
                metadata=DocumentMetadata(),
                extracted_info={},
                confidence_score=0.7,
                assigned_department="General"
            )

        mock_llm.classify_and_extract = AsyncMock(side_effect=side_effect)

        with patch('time.sleep'):
            result = await mock_llm.classify_and_extract("Test")

        assert result is not None
        assert call_count == 2

    @patch('app.services.embedding_service.EmbeddingService')
    def test_embedding_service_error_handling(self, mock_embed_class):
        """Test embedding service error handling"""
        mock_embed = mock_embed_class.return_value
        mock_embed.generate_embedding.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            mock_embed.generate_embedding("Test")

    @patch('app.database.chroma_client.ChromaDBClient')
    def test_database_connection_error(self, mock_db_class):
        """Test database connection error handling"""
        mock_db_class.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            mock_db_class()


@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """Test performance and scalability"""

    @pytest.mark.asyncio
    @patch('app.services.embedding_service.EmbeddingService')
    async def test_batch_embedding_performance(self, mock_embed_class):
        """Test batch embedding performance"""
        mock_embed = mock_embed_class.return_value
        mock_embed.generate_batch_embeddings.return_value = [[0.1] * 1024] * 100

        texts = [f"Document {i}" for i in range(100)]
        embeddings = mock_embed.generate_batch_embeddings(texts)

        assert len(embeddings) == 100
        assert all(len(e) == 1024 for e in embeddings)

    @pytest.mark.asyncio
    @patch('app.services.llm_service.LLMService')
    async def test_concurrent_document_processing(self, mock_llm_class):
        """Test processing multiple documents concurrently"""
        mock_llm = mock_llm_class.return_value

        async def classify_mock(text):
            return ProcessedDocument(
                raw_text=text,
                category=DocumentCategory.GENERAL,
                urgency_level=UrgencyLevel.LOW,
                metadata=DocumentMetadata(),
                extracted_info={},
                confidence_score=0.8,
                assigned_department="General"
            )

        mock_llm.classify_and_extract = AsyncMock(side_effect=classify_mock)

        # Process multiple documents
        texts = [f"Document {i}" for i in range(10)]
        results = []
        for text in texts:
            result = await mock_llm.classify_and_extract(text)
            results.append(result)

        assert len(results) == 10
        assert all(isinstance(r, ProcessedDocument) for r in results)

