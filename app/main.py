from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from app.services.ocr_service import MistralDocumentAIService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.routing_service import RoutingService
from app.database.chroma_client import ChromaDBClient
from app.models.document import ProcessedDocument

app = FastAPI(
    title="Bank Document Classification System",
    description="AI-powered document processing for German bank using Mistral Document AI",
    version="1.0.0"
)

# Initialize services
document_ai_service = MistralDocumentAIService()
llm_service = LLMService()
embedding_service = EmbeddingService()
routing_service = RoutingService()
db_client = ChromaDBClient()


@app.post("/process-document")
async def process_document(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        source_type: str = "scan"  # scan, email, digital
):
    """
    Main endpoint to process incoming documents using Mistral Document AI
    """
    try:
        # Step 1: Read file content
        content = await file.read()

        # Step 2: Process with Mistral Document AI for intelligent extraction
        document_structure = await document_ai_service.process_document(
            document=content,
            document_type=file.filename.split('.')[-1].lower(),
            source_type=source_type
        )

        # Step 3: Format structured data for LLM classification
        formatted_text = document_ai_service.format_for_downstream(document_structure)

        # Step 4: Classify and extract information using LLM
        processed_doc = await llm_service.classify_and_extract(formatted_text)

        # Enhance with Document AI extracted fields
        if document_structure.forms.get("customer_id"):
            processed_doc.metadata.customer_id = document_structure.forms["customer_id"]
        if document_structure.forms.get("account_number"):
            processed_doc.metadata.account_number = document_structure.forms["account_number"]
        if document_structure.forms.get("iban"):
            processed_doc.extracted_info["iban"] = document_structure.forms["iban"]

        # Step 5: Generate embedding for semantic search
        embedding = await embedding_service.generate_embedding(formatted_text)
        processed_doc.embedding = embedding

        # Step 6: Store in vector database with rich metadata
        await db_client.store_document(
            document_id=processed_doc.id,
            text=formatted_text,
            embedding=embedding,
            metadata={
                "category": processed_doc.category,
                "urgency": processed_doc.urgency_level,
                "customer_id": processed_doc.metadata.customer_id,
                "processed_at": processed_doc.processed_at.isoformat(),
                "document_type": document_structure.metadata.get("document_type"),
                "language": document_structure.metadata.get("language"),
                "quality_score": document_structure.metadata.get("quality_score"),
                "has_tables": len(document_structure.tables) > 0,
                "has_forms": len(document_structure.forms) > 0,
                "extraction_confidence": document_structure.confidence_scores.get("overall", 0)
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
                "category": processed_doc.category,
                "urgency": processed_doc.urgency_level,
                "department": processed_doc.assigned_department,
                "requires_immediate_attention": processed_doc.requires_immediate_attention,
                "confidence_score": processed_doc.confidence_score,
                "extracted_info": processed_doc.extracted_info,
                "document_ai_metadata": {
                    "quality_score": document_structure.metadata.get("quality_score"),
                    "extraction_confidence": document_structure.confidence_scores,
                    "detected_language": document_structure.metadata.get("language"),
                    "extracted_fields": list(document_structure.forms.keys())
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-email")
async def process_email_document(
        email_content: str,
        attachments: List[UploadFile] = File(None),
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process email with potential attachments using Mistral Document AI
    """
    try:
        all_processed = []

        # Process email body
        email_structure = await document_ai_service.process_document(
            document=email_content,
            document_type="text",
            source_type="email"
        )

        formatted_email = document_ai_service.format_for_downstream(email_structure)
        email_doc = await llm_service.classify_and_extract(formatted_email)
        all_processed.append(email_doc)

        # Process attachments if any
        if attachments:
            for attachment in attachments:
                content = await attachment.read()
                att_structure = await document_ai_service.process_document(
                    document=content,
                    document_type=attachment.filename.split('.')[-1].lower(),
                    source_type="email"
                )

                formatted_att = document_ai_service.format_for_downstream(att_structure)
                att_doc = await llm_service.classify_and_extract(formatted_att)
                all_processed.append(att_doc)

        # Determine primary document and route
        primary_doc = max(all_processed, key=lambda x: x.confidence_score)

        # Store all documents
        for doc in all_processed:
            embedding = await embedding_service.generate_embedding(doc.raw_text)
            await db_client.store_document(
                document_id=doc.id,
                text=doc.raw_text,
                embedding=embedding,
                metadata={
                    "category": doc.category,
                    "urgency": doc.urgency_level,
                    "customer_id": doc.metadata.customer_id,
                    "source": "email"
                }
            )

        # Route primary document
        background_tasks.add_task(
            routing_service.route_document,
            primary_doc
        )

        return JSONResponse(
            status_code=200,
            content={
                "primary_document": {
                    "document_id": primary_doc.id,
                    "category": primary_doc.category,
                    "urgency": primary_doc.urgency_level,
                    "department": primary_doc.assigned_department
                },
                "all_documents": [
                    {"id": doc.id, "category": doc.category}
                    for doc in all_processed
                ]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document/{document_id}/analysis")
async def get_document_analysis(document_id: str):
    """
    Get detailed analysis of a processed document including Document AI insights
    """
    try:
        document = await db_client.get_document_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Return comprehensive analysis
        return JSONResponse(
            status_code=200,
            content={
                "document_id": document_id,
                "metadata": document.get("metadata", {}),
                "analysis": {
                    "extraction_quality": document.get("metadata", {}).get("quality_score", 0),
                    "confidence_scores": document.get("metadata", {}).get("extraction_confidence", {}),
                    "has_structured_data": {
                        "tables": document.get("metadata", {}).get("has_tables", False),
                        "forms": document.get("metadata", {}).get("has_forms", False)
                    },
                    "language": document.get("metadata", {}).get("language", "unknown"),
                    "document_type": document.get("metadata", {}).get("document_type", "unknown")
                }
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-similar")
async def search_similar_documents(
        query: str,
        n_results: int = 5,
        category: Optional[str] = None
):
    """
    Search for similar documents using semantic search
    """
    try:
        # Generate embedding for query
        query_embedding = await embedding_service.generate_embedding(query)

        # Prepare filter if category specified
        filter_metadata = {"category": category} if category else None

        # Search in vector database
        results = await db_client.search_similar_documents(
            query_embedding=query_embedding,
            n_results=n_results,
            filter_metadata=filter_metadata
        )

        return JSONResponse(
            status_code=200,
            content={
                "query": query,
                "results": [
                    {
                        "document_id": results["ids"][i],
                        "similarity_score": 1 - results["distances"][i],
                        "metadata": results["metadatas"][i]
                    }
                    for i in range(len(results["ids"]))
                ]
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document/{document_id}")
async def get_document(document_id: str):
    """
    Retrieve specific document by ID
    """
    try:
        document = await db_client.get_document_by_id(document_id)

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Bank Document Classification System"}