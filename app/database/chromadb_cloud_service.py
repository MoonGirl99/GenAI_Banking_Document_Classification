# app/app/database/chroma_client.py
import os
import chromadb
from chromadb import CloudClient

CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = os.getenv("CHROMA_TENANT")
CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")

if not (CHROMA_API_KEY and CHROMA_TENANT and CHROMA_DATABASE):
    raise RuntimeError("Missing CHROMA_* env vars. Set CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE")

client = None
try:
    client = CloudClient(
        api_key=CHROMA_API_KEY,
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
    )
except Exception:
    client = chromadb.HttpClient(
        host="api.trychroma.com",
        port=8000,
        ssl=True,
        headers={"x-chroma-token": CHROMA_API_KEY},
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
    )

_COLLECTION_NAME = "bank_documents"

def get_collection():
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"project": "genai_doc_classification"}
    )
