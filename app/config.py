from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    # Mistral AI Configuration
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-large-latest"
    MISTRAL_EMBEDDING_MODEL: str = "mistral-embed"

    # ChromaDB Configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "bank_documents"

    # Department Routing
    DEPARTMENT_EMAILS: Dict[str, str] = {
        "loan_applications": "loans@bank.de",
        "account_inquiries": "accounts@bank.de",
        "complaints": "complaints@bank.de",
        "kyc_updates": "compliance@bank.de",
        "general_correspondence": "info@bank.de"
    }

    # Urgency Thresholds
    HIGH_URGENCY_KEYWORDS: list = [
        "urgent", "dringend", "immediately", "sofort",
        "complaint", "beschwerde", "fraud", "betrug"
    ]

    class Config:
        env_file = ".env"


settings = Settings()