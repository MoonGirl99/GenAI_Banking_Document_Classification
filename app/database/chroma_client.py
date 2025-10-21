import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import uuid
from app.config import settings


class ChromaDBClient:
    def __init__(self):
        # Add retry logic and better error handling
        import time
        max_retries = 5
        for i in range(max_retries):
            try:
                self.client = chromadb.HttpClient(
                    host=settings.CHROMA_HOST,
                    port=settings.CHROMA_PORT,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                self.collection = self._get_or_create_collection()
                print(f"✅ Connected to ChromaDB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
                break
            except Exception as e:
                if i < max_retries - 1:
                    print(f"⏳ Waiting for ChromaDB... (attempt {i+1}/{max_retries})")
                    time.sleep(2)
                else:
                    raise Exception(f"Failed to connect to ChromaDB after {max_retries} attempts: {e}")


    def _get_or_create_collection(self):
        """Get or create a documents collection"""
        try:
            return self.client.get_collection(settings.CHROMA_COLLECTION_NAME)
        except:
            return self.client.create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"description": "Bank documents collection"}
            )

    def store_document(
            self,
            document_id: str,
            text: str,
            embedding: List[float],
            metadata: Dict
    ):
        """Store document with embedding in ChromaDB"""
        self.collection.add(
            ids=[document_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def search_similar_documents(
            self,
            query_embedding: List[float],
            n_results: int = 5,
            filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """Search for similar documents using vector similarity"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )

        return {
            "ids": results["ids"][0],
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0]
        }

    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """Retrieve specific document by ID"""
        results = self.collection.get(
            ids=[document_id],
            include=["documents", "metadatas", "embeddings"]
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "document": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None