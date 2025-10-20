from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import uuid

class DocumentCategory(str, Enum):
    LOAN_APPLICATION = "loan_applications"
    ACCOUNT_INQUIRY = "account_inquiries"
    COMPLAINT = "complaints"
    KYC_UPDATE = "kyc_updates"
    GENERAL = "general_correspondence"

class UrgencyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DocumentMetadata(BaseModel):
    customer_id: Optional[str] = None
    account_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    subject: Optional[str] = None
    language: str = "de"

class ProcessedDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str
    category: DocumentCategory
    urgency_level: UrgencyLevel
    metadata: DocumentMetadata
    extracted_info: Dict
    confidence_score: float
    processed_at: datetime = Field(default_factory=datetime.now)
    embedding: Optional[List[float]] = None
    assigned_department: str
    requires_immediate_attention: bool = False