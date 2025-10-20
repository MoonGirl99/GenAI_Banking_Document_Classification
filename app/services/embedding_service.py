from mistralai import Mistral
import numpy as np
from typing import List
from app.config import settings


class EmbeddingService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embeddings using Mistral's embedding model
        """
        try:
            response = await self.client.embeddings.create(
                model=settings.MISTRAL_EMBEDDING_MODEL,
                inputs=[text]
            )

            return response.data[0].embedding

        except Exception as e:
            raise Exception(f"Embedding generation failed: {str(e)}")

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        """
        try:
            response = await self.client.embeddings.create(
                model=settings.MISTRAL_EMBEDDING_MODEL,
                inputs=texts
            )

            return [item.embedding for item in response.data]

        except Exception as e:
            raise Exception(f"Batch embedding generation failed: {str(e)}")