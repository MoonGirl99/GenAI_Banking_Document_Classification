from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from pydantic import BaseModel
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


# Pydantic models for request bodies
class TextInput(BaseModel):
    text: str
    filename: Optional[str] = "pasted_text.txt"


@app.get("/")
def home():
    """Serve the web UI"""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/health")
def health():
    return {
        "api": "healthy",
        "chromadb": db_client.collection.count(),  # Check DB connection
        "mistral": "ok"  # Could add API key validation
    }

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
        # Filter out None values from metadata to avoid ChromaDB deserialization errors
        metadata = {
            "category": processed_doc.category.value,
            "urgency": processed_doc.urgency_level.value,
            "processed_at": processed_doc.processed_at.isoformat(),
            "filename": file.filename
        }

        # Add optional fields only if they exist
        if processed_doc.metadata.customer_id:
            metadata["customer_id"] = processed_doc.metadata.customer_id
        else:
            metadata["customer_id_missing"] = "true"  # Flag for missing customer ID

        if processed_doc.metadata.account_number:
            metadata["account_number"] = processed_doc.metadata.account_number
        else:
            metadata["account_number_missing"] = "true"  # Flag for missing account number

        if processed_doc.metadata.email:
            metadata["email"] = processed_doc.metadata.email

        if processed_doc.metadata.phone:
            metadata["phone"] = processed_doc.metadata.phone

        db_client.store_document(
            document_id=processed_doc.id,
            text=text_content,
            embedding=embedding,
            metadata=metadata
        )

        # Step 7: Route document (in background)
        background_tasks.add_task(
            routing_service.route_document,
            processed_doc
        )

        # Create alerts for missing critical data
        alerts = []
        if not processed_doc.metadata.customer_id:
            alerts.append("Customer ID is missing from this document")
        if not processed_doc.metadata.account_number:
            alerts.append("Account number is missing from this document")
        if not processed_doc.metadata.email and not processed_doc.metadata.phone:
            alerts.append("No contact information (email or phone) found in this document")

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
                },
                "alerts": alerts if alerts else None
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-text")
async def process_text(
        text_input: TextInput,
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process text directly without file upload (for copy-paste functionality)
    """
    try:
        # Validate text input
        if not text_input.text or not text_input.text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")

        text_content = text_input.text.strip()

        # Step 1: Classify and extract information using LLM
        processed_doc = await llm_service.classify_and_extract(text_content)

        # Step 2: Generate embedding for semantic search
        embedding = embedding_service.generate_embedding(text_content)
        processed_doc.embedding = embedding

        # Step 3: Store in vector database
        metadata = {
            "category": processed_doc.category.value,
            "urgency": processed_doc.urgency_level.value,
            "processed_at": processed_doc.processed_at.isoformat(),
            "filename": text_input.filename
        }

        # Add optional fields only if they exist
        if processed_doc.metadata.customer_id:
            metadata["customer_id"] = processed_doc.metadata.customer_id
        else:
            metadata["customer_id_missing"] = "true"

        if processed_doc.metadata.account_number:
            metadata["account_number"] = processed_doc.metadata.account_number
        else:
            metadata["account_number_missing"] = "true"

        if processed_doc.metadata.email:
            metadata["email"] = processed_doc.metadata.email

        if processed_doc.metadata.phone:
            metadata["phone"] = processed_doc.metadata.phone

        db_client.store_document(
            document_id=processed_doc.id,
            text=text_content,
            embedding=embedding,
            metadata=metadata
        )

        # Step 4: Route document (in background)
        background_tasks.add_task(
            routing_service.route_document,
            processed_doc
        )

        # Create alerts for missing critical data
        alerts = []
        if not processed_doc.metadata.customer_id:
            alerts.append("Customer ID is missing from this document")
        if not processed_doc.metadata.account_number:
            alerts.append("Account number is missing from this document")
        if not processed_doc.metadata.email and not processed_doc.metadata.phone:
            alerts.append("No contact information (email or phone) found in this document")

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
                },
                "alerts": alerts if alerts else None
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


# --- Add below your other @app.get routes in main.py ---

@app.get("/api/admin/collection-stats")
def collection_stats():
    try:
        name = db_client.collection.name
        count = db_client.collection.count()
        return {"collection": name, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/peek")
def peek(limit: int = 5, offset: int = 0, include_embeddings: bool = False):
    try:
        # Only allowed keys here; IDs come back regardless
        include = ["documents", "metadatas"]
        if include_embeddings:
            include.append("embeddings")

        res = db_client.collection.get(limit=limit, offset=offset, include=include)

        n = len(res.get("ids", []))
        items = []
        for i in range(n):
            emb_preview = None
            if include_embeddings and res.get("embeddings") is not None:
                raw = res["embeddings"][i]
                try:
                    emb_list = raw.tolist() if hasattr(raw, "tolist") else list(raw)
                    emb_preview = emb_list[:8]  # small preview
                except Exception:
                    emb_preview = None

            items.append({
                "id": res["ids"][i],
                "doc": (res.get("documents") or [None])[i],
                "meta": (res.get("metadatas") or [None])[i],
                "embedding_preview": emb_preview
            })

        return {"limit": limit, "offset": offset, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/vector-stats")
def vector_stats(sample: int = 50):
    """
    Inspect sample embeddings for dimension consistency and vector norms.
    Fully safe against NumPy truth-value ambiguity.
    """
    try:
        import numpy as np
        res = db_client.collection.get(limit=sample, include=["embeddings"])
        raw_embs = res.get("embeddings", [])

        valid_embs = []
        for e in raw_embs:
            if e is None:
                continue
            # Handle numpy arrays, lists, or nested structures robustly
            try:
                arr = np.array(e, dtype=np.float32)
                # Explicit check: ensure the array has *any* finite elements
                if np.any(np.isfinite(arr)) and arr.size > 0:
                    valid_embs.append(arr)
            except Exception:
                continue

        if len(valid_embs) == 0:
            raise HTTPException(status_code=400, detail="No valid embeddings found.")

        dims = [emb.shape[0] for emb in valid_embs]
        norms = [float(np.linalg.norm(emb)) for emb in valid_embs if np.any(emb)]

        return {
            "sample": len(valid_embs),
            "dim_unique": sorted(list(set(dims))),
            "dim_all_equal": (len(set(dims)) == 1),
            "norm_min": round(min(norms), 6),
            "norm_avg": round(sum(norms) / len(norms), 6),
            "norm_max": round(max(norms), 6),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents-by-category")
def get_documents_by_category():
    """
    Get all documents grouped by category
    """
    try:
        # Get all documents from ChromaDB
        results = db_client.collection.get(
            include=["metadatas", "documents"]
        )

        # Group by category
        documents_by_category = {}
        for i, doc_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            category = metadata.get("category", "general_correspondence")

            if category not in documents_by_category:
                documents_by_category[category] = []

            documents_by_category[category].append({
                "document_id": doc_id,
                "filename": metadata.get("filename", "Unknown"),
                "customer_id": metadata.get("customer_id"),
                "urgency": metadata.get("urgency"),
                "processed_at": metadata.get("processed_at")
            })

        return JSONResponse(
            status_code=200,
            content={"categories": documents_by_category}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_with_document(request: dict):
    """
    Chat with LLM about documents - searches database for relevant context
    """
    try:
        query = request.get("query")
        document_id = request.get("document_id")
        chat_history = request.get("chat_history", [])

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # Get document context if document_id provided
        context = ""
        if document_id:
            doc = db_client.get_document_by_id(document_id)
            if doc:
                context = f"Document Context:\n{doc['document']}\n\nMetadata: {doc['metadata']}\n\n"
        else:
            # Search for relevant documents using semantic search
            try:
                query_embedding = embedding_service.generate_embedding(query)
                search_results = db_client.search_similar_documents(
                    query_embedding=query_embedding,
                    n_results=3  # Get top 3 relevant documents
                )

                if search_results["ids"]:
                    context = "Relevant Documents from Database:\n\n"
                    for i in range(len(search_results["ids"])):
                        doc_id = search_results["ids"][i]
                        doc_text = search_results["documents"][i]
                        doc_meta = search_results["metadatas"][i]
                        similarity = 1 - search_results["distances"][i]

                        context += f"Document {i+1} (ID: {doc_id}, Similarity: {similarity:.2f}):\n"
                        context += f"Category: {doc_meta.get('category', 'N/A')}\n"
                        context += f"Urgency: {doc_meta.get('urgency', 'N/A')}\n"
                        context += f"Filename: {doc_meta.get('filename', 'N/A')}\n"
                        context += f"Content Preview: {doc_text[:500]}...\n\n"

                    # Get all documents if query is about listing/viewing all
                    if any(keyword in query.lower() for keyword in ['all', 'list', 'show me', 'find all', 'get all']):
                        all_docs = db_client.collection.get(include=["metadatas", "documents"])
                        context += f"\n\nTotal Documents in Database: {len(all_docs['ids'])}\n"

                        # Group by category for summary
                        category_counts = {}
                        for meta in all_docs["metadatas"]:
                            cat = meta.get("category", "unknown")
                            category_counts[cat] = category_counts.get(cat, 0) + 1

                        context += "Documents by Category:\n"
                        for cat, count in category_counts.items():
                            context += f"- {cat}: {count} document(s)\n"

            except Exception as e:
                print(f"Search error: {e}")
                # Continue without search results
                context = "Note: Unable to search database at this moment, providing general assistance.\n\n"

        # Use LLM service to generate response
        response = await llm_service.chat_with_context(query, context, chat_history)

        return JSONResponse(
            status_code=200,
            content={"response": response}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
