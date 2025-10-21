# app/app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from app.services.ocr_service import MistralOCRService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.routing_service import RoutingService
from app.database.chroma_client import get_collection

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

# Single Chroma collection (Cloud)
collection = get_collection()

@app.get("/")
def home():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Bank Document Classification System"}

@app.post("/process-document")
async def process_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    try:
        # 1) Read file
        content = await file.read()

        # 2) OCR
        document_structure = ocr_service.process_document(
            document=content,
            document_type=file.filename.split('.')[-1].lower()
        )
        text_content = document_structure.raw_text

        # 3) LLM classify/extract
        processed_doc = await llm_service.classify_and_extract(text_content)

        # 4) Embedding
        embedding = embedding_service.generate_embedding(text_content)

        # 5) Store in Chroma Cloud (ids, documents, metadatas, embeddings)
        collection.add(
            ids=[processed_doc.id],
            documents=[text_content],
            metadatas=[{
                "category": processed_doc.category.value,
                "urgency": processed_doc.urgency_level.value,
                "customer_id": processed_doc.metadata.customer_id,
                "processed_at": processed_doc.processed_at.isoformat(),
                "filename": file.filename
            }],
            embeddings=[embedding]
        )

        # 6) Background routing
        background_tasks.add_task(routing_service.route_document, processed_doc)

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
    try:
        # Embed query
        query_embedding = embedding_service.generate_embedding(query)

        # Query Chroma Cloud (include distances, docs, metas)
        res = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )

        # Chroma returns lists per query; index 0 is our only query
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        items = []
        for i in range(len(ids)):
            preview = (docs[i] or "")[:200] + "..." if docs and len(docs) > i and docs[i] else ""
            # Cosine distance -> similarity ~ (1 - distance)
            sim = 1.0 - float(dists[i]) if dists and len(dists) > i else 0.0
            items.append({
                "document_id": ids[i],
                "text_preview": preview,
                "metadata": metas[i] if metas and len(metas) > i else None,
                "similarity": sim
            })

        return JSONResponse(status_code=200, content={"query": query, "results": items})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/document/{document_id}")
def get_document(document_id: str):
    try:
        res = collection.get(ids=[document_id], include=["documents", "metadatas"])
        ids = res.get("ids", [])
        if not ids:
            raise HTTPException(status_code=404, detail="Document not found")
        return {
            "id": ids[0],
            "document": (res.get("documents") or [None])[0],
            "metadata": (res.get("metadatas") or [None])[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----- Admin/Debug endpoints (updated to use 'collection') -----

@app.get("/api/admin/inspect-embeddings")
async def inspect_embeddings(limit: int = 10, offset: int = 0):
    try:
        results = collection.get(limit=limit, offset=offset, include=["embeddings", "metadatas", "documents"])
        documents = []
        for i in range(len(results.get("ids", []))):
            emb = (results.get("embeddings") or [None])[i]
            meta = (results.get("metadatas") or [None])[i]
            doc  = (results.get("documents") or [None])[i]
            documents.append({
                "id": results["ids"][i],
                "document": doc,
                "embedding": (emb[:5] if emb else None),
                "embedding_dim": (len(emb) if emb else 0),
                "metadata": meta,
            })
        return {"count": len(results.get("ids", [])), "documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/debug-storage")
async def debug_storage():
    try:
        results = collection.get(limit=1, include=["embeddings", "metadatas", "documents"])
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

@app.get("/api/admin/collection-stats")
def collection_stats():
    try:
        return {"collection": collection.name, "count": collection.count()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/peek")
def peek(limit: int = 5, offset: int = 0, include_embeddings: bool = False):
    try:
        include = ["documents", "metadatas"]
        if include_embeddings:
            include.append("embeddings")
        res = collection.get(limit=limit, offset=offset, include=include)

        n = len(res.get("ids", []))
        items = []
        for i in range(n):
            emb_preview = None
            if include_embeddings and res.get("embeddings") is not None:
                raw = res["embeddings"][i]
                try:
                    emb_preview = (raw.tolist() if hasattr(raw, "tolist") else list(raw))[:8]
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
    try:
        import numpy as np
        res = collection.get(limit=sample, include=["embeddings"])
        raw_embs = res.get("embeddings", []) or []

        valid = []
        for e in raw_embs:
            if e is None:
                continue
            try:
                arr = np.array(e, dtype=np.float32)
                if np.any(np.isfinite(arr)) and arr.size > 0:
                    valid.append(arr)
            except Exception:
                continue

        if not valid:
            raise HTTPException(status_code=400, detail="No valid embeddings found.")

        dims = [emb.shape[0] for emb in valid]
        norms = [float(np.linalg.norm(emb)) for emb in valid if emb.size > 0]

        return {
            "sample": len(valid),
            "dim_unique": sorted(list(set(dims))),
            "dim_all_equal": (len(set(dims)) == 1),
            "norm_min": round(min(norms), 6),
            "norm_avg": round(sum(norms) / len(norms), 6),
            "norm_max": round(max(norms), 6),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/chroma-ping")
def chroma_ping():
    col = get_collection()
    return {"collection": col.name, "count": col.count()}
