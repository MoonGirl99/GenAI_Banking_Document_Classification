"""
Unit tests for ChromaDB client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.database.chroma_client import ChromaDBClient


@pytest.mark.unit
class TestChromaDBClient:
    """Test ChromaDBClient class"""

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_client_initialization(self, mock_chromadb, mock_env_vars):
        """Test ChromaDB client initialization"""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "bank_documents"
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()

        assert client.collection is not None
        assert client.collection.name == "bank_documents"
        mock_chromadb.assert_called_once()

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_store_document_success(self, mock_chromadb, mock_chromadb_collection):
        """Test successful document storage"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()

        # Store document
        client.store_document(
            document_id="doc-123",
            text="Sample document text",
            embedding=[0.1] * 1024,
            metadata={"category": "loan_applications", "urgency": "high"}
        )

        mock_chromadb_collection.add.assert_called_once()
        call_args = mock_chromadb_collection.add.call_args
        assert "doc-123" in call_args.kwargs["ids"]

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_store_document_with_metadata(self, mock_chromadb, mock_chromadb_collection):
        """Test storing document with metadata"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        metadata = {
            "category": "complaints",
            "urgency": "high",
            "customer_id": "CUST-123",
            "processed_at": "2024-01-01T00:00:00"
        }

        client.store_document(
            document_id="doc-456",
            text="Complaint text",
            embedding=[0.2] * 1024,
            metadata=metadata
        )

        call_args = mock_chromadb_collection.add.call_args
        assert call_args.kwargs["metadatas"][0]["category"] == "complaints"
        assert call_args.kwargs["metadatas"][0]["customer_id"] == "CUST-123"

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_search_similar_documents(self, mock_chromadb, mock_chromadb_collection):
        """Test searching for similar documents"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        query_embedding = [0.1] * 1024

        results = client.search_similar_documents(
            query_embedding=query_embedding,
            n_results=5
        )

        assert "ids" in results
        assert "distances" in results
        assert "documents" in results
        assert "metadatas" in results
        mock_chromadb_collection.query.assert_called_once()

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_search_with_filter(self, mock_chromadb, mock_chromadb_collection):
        """Test searching with metadata filter"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()

        results = client.search_similar_documents(
            query_embedding=[0.1] * 1024,
            n_results=3,
            where={"category": "loan_applications"}
        )

        call_args = mock_chromadb_collection.query.call_args
        assert "where" in call_args.kwargs

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_get_document_by_id(self, mock_chromadb, mock_chromadb_collection):
        """Test retrieving document by ID"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        doc = client.get_document_by_id("doc-123")

        assert doc is not None
        mock_chromadb_collection.get.assert_called_once()

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_get_nonexistent_document(self, mock_chromadb):
        """Test retrieving non-existent document"""
        mock_collection = Mock()
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        doc = client.get_document_by_id("nonexistent")

        assert doc is None

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_delete_document(self, mock_chromadb, mock_chromadb_collection):
        """Test deleting a document"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        client.delete_document("doc-to-delete")

        mock_chromadb_collection.delete.assert_called_once_with(ids=["doc-to-delete"])

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_collection_count(self, mock_chromadb, mock_chromadb_collection):
        """Test getting collection count"""
        mock_chromadb_collection.count.return_value = 42
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()
        count = client.collection.count()

        assert count == 42

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_handle_connection_error(self, mock_chromadb):
        """Test handling of connection errors"""
        mock_chromadb.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            ChromaDBClient()

    @patch('app.database.chroma_client.chromadb.HttpClient')
    def test_store_multiple_documents(self, mock_chromadb, mock_chromadb_collection):
        """Test storing multiple documents"""
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_chromadb_collection
        mock_chromadb.return_value = mock_client

        client = ChromaDBClient()

        # Store multiple documents
        for i in range(3):
            client.store_document(
                document_id=f"doc-{i}",
                text=f"Document {i}",
                embedding=[0.1 * i] * 1024,
                metadata={"index": i}
            )

        assert mock_chromadb_collection.add.call_count == 3
