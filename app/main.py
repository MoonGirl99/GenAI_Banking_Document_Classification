from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import uuid
import os
from app.config import settings
from app.services.ocr_service import MistralOCRService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.routing_service import RoutingService
from app.database.chroma_client import ChromaDBClient
from app.models.document import ProcessedDocument

app = FastAPI(
    title="Bank Document Classification System",
    description="AI-powered document processing for German bank using Mistral AI",
    version="1.0.0"
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize services
ocr_service = MistralOCRService()
llm_service = LLMService()
embedding_service = EmbeddingService()
routing_service = RoutingService()
db_client = ChromaDBClient()


@app.get("/")
def home():
    """Serve the web UI"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/health")
def health_check():
    """API health check endpoint"""
    return {"status": "healthy", "service": "Bank Document Classification System"}


@app.post("/process-document")
async def process_document(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Main endpoint to process incoming documents using Mistral AI
    """
    try:
        # Step 1: Read file content
        content = await file.read()

        # Step 2: Process with Mistral OCR for text extraction
        document_structure = ocr_service.process_document(
            document=content,
            document_type=file.filename.split('.')[-1].lower()
        )

        # Step 3: Use the extracted text
        text_content = document_structure.raw_text

        # Step 4: Classify and extract information using LLM
        processed_doc = await llm_service.classify_and_extract(text_content)  # Add await

        # Step 5: Generate embedding for semantic search
        embedding = embedding_service.generate_embedding(text_content)
        processed_doc.embedding = embedding

        # Step 6: Store in vector database
        db_client.store_document(
            document_id=processed_doc.id,
            text=text_content,
            embedding=embedding,
            metadata={
                "category": processed_doc.category.value,
                "urgency": processed_doc.urgency_level.value,
                "customer_id": processed_doc.metadata.customer_id,
                "processed_at": processed_doc.processed_at.isoformat(),
                "filename": file.filename
            }
        )

        # Step 7: Route document (in background)
        background_tasks.add_task(
            routing_service.route_document,
            processed_doc
        )

        return JSONResponse(
            status_code=200,
            content={
                "document_id": processed_doc.id,
                "category": processed_doc.category.value,
                "urgency": processed_doc.urgency_level.value,
                "department": processed_doc.assigned_department,
                "requires_immediate_attention": processed_doc.requires_immediate_attention,
                "confidence_score": processed_doc.confidence_score,
                "extracted_info": processed_doc.extracted_info,
                "metadata": {
                    "customer_id": processed_doc.metadata.customer_id,
                    "account_number": processed_doc.metadata.account_number
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-documents")
def search_documents(query: str, n_results: int = 5):
    """
    Search for similar documents using semantic search
    """
    try:
        # Generate embedding for the query
        query_embedding = embedding_service.generate_embedding(query)

        # Search in ChromaDB
        results = db_client.search_similar_documents(
            query_embedding=query_embedding,
            n_results=n_results
        )

        return JSONResponse(
            status_code=200,
            content={
                "query": query,
                "results": [
                    {
                        "document_id": results["ids"][i],
                        "text_preview": results["documents"][i][:200] + "...",
                        "metadata": results["metadatas"][i],
                        "similarity": float(1 - results["distances"][i])
                    }
                    for i in range(len(results["ids"]))
                ]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document/{document_id}")
def get_document(document_id: str):
    """
    Get a specific document by ID
    """
    try:
        document = db_client.get_document_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return JSONResponse(
            status_code=200,
            content=document
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/inspect-embeddings")
async def inspect_embeddings(limit: int = 10, offset: int = 0):
    """
    Retrieve embeddings and metadata for inspection.
    Args:
        limit: Number of documents to return.
        offset: Pagination offset.
    Returns:
        List of documents with embeddings and metadata.
    """
    try:
        results = db_client.collection.get(
            limit=limit,
            offset=offset,
            include=["embeddings", "metadatas", "documents"]  # Remove "ids" from here
        )
        # Format the response for clarity
        documents = []
        for i, (doc_id, embedding, metadata, document) in enumerate(zip(
            results["ids"],  # ids are always returned
            results["embeddings"],
            results.get("metadatas", []),
            results.get("documents", [])
        )):
            documents.append({
                "id": doc_id,
                "document": document,
                "embedding": embedding[:5] if embedding else None,  # Show first 5 dims for brevity
                "embedding_dim": len(embedding) if embedding else 0,
                "metadata": metadata,
            })
        return {"count": len(results["ids"]), "documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/debug-storage")
async def debug_storage():
    """Debug what's actually stored"""
    try:
        results = db_client.collection.get(
            limit=1,
            include=["embeddings", "metadatas", "documents"]
        )

        return {
            "ids": results.get("ids", []),
            "embeddings_key_exists": "embeddings" in results,
            "embeddings_value": str(type(results.get("embeddings"))),
            "embeddings_length": len(results.get("embeddings", [])),
            "raw_result_keys": list(results.keys())
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}