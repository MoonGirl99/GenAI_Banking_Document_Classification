from pydantic_settings import BaseSettings
from typing import Dict


class Settings(BaseSettings):
    # Mistral AI Configuration
    MISTRAL_API_KEY: str
    MISTRAL_MODEL: str = "mistral-medium-2508"
    MISTRAL_EMBEDDING_MODEL: str = "mistral-embed"
    MISTRAL_OCR_MODEL: str = "mistral-ocr-2505"

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
        # English urgency & escalation
        "urgent", "immediate", "immediately", "asap", "right away", "straight away",
        "important", "priority", "critical", "emergency", "escalate", "escalation",
        "attention", "please respond", "please reply", "reply soon",
        "resolve quickly", "action required", "requires attention", "follow up",

        # German urgency & escalation
        "dringend", "sofort", "unverzüglich", "eilig", "schnellstmöglich",
        "so schnell wie möglich", "umgehend", "sofortige bearbeitung",
        "rückmeldung erforderlich", "bitte antworten", "bitte um rückmeldung",

        # Complaints & disputes
        "complaint", "beschwerde", "issue", "problem", "dispute", "reklamation",
        "unzufrieden", "nicht zufrieden", "unacceptable", "fault", "error",
        "mistake", "wrong charge", "wrong account", "unauthorized",

        # Fraud, scams, security
        "fraud", "scam", "betrug", "betrügerisch", "phishing", "hacker",
        "suspicious", "suspicious activity", "compromised", "stolen", "lost card",
        "card blocked", "block card", "lock account", "unauthorized access",

        # Payments & finance issues
        "payment failed", "transaction failed", "transfer failed", "delay",
        "delayed", "überweisung fehlgeschlagen", "zahlung fehlgeschlagen",
        "konto gesperrt", "account blocked", "limit exceeded", "limit reached",

        # Customer threats or cancellations
        "cancel account", "close account", "kündigung", "stornieren",
        "termination", "end contract", "kündigen", "drohe zu wechseln",
        "switch bank", "lose customer", "beschwerde einreichen",

        # Legal / escalation
        "lawyer", "anwalt", "rechtliche schritte", "legal action",
        "data breach", "datenschutzverletzung", "gdpr", "dsgvo", "privacy violation"
    ]

    class Config:
        env_file = ".env"


settings = Settings()