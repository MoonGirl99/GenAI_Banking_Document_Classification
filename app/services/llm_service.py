import time
from mistralai import Mistral
import json
from app.config import settings
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata


class LLMService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)

    async def classify_and_extract(self, text: str) -> ProcessedDocument:
        """
        Use Mistral LLM to classify document and extract key information
        """
        prompt = self._create_classification_prompt(text)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.client.chat.complete(
                    model=settings.MISTRAL_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )

                # Parse the JSON response
                result = json.loads(response.choices[0].message.content)

                # Create ProcessedDocument
                processed_doc = ProcessedDocument(
                    raw_text=text,
                    category=DocumentCategory(result["category"]),
                    urgency_level=UrgencyLevel(result["urgency"]),
                    metadata=DocumentMetadata(**result["metadata"]),
                    extracted_info=result["extracted_info"],
                    confidence_score=result["confidence_score"],
                    assigned_department=self._get_department(result["category"]),
                    requires_immediate_attention=(result["urgency"] == "high")
                )

                return processed_doc

            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait = 2 ** attempt  # Exponential backoff
                    print(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    raise Exception(f"LLM classification failed: {str(e)}")
        else:
            raise Exception("LLM classification failed after max retries")

    def _get_system_prompt(self) -> str:
        return """You are an AI assistant specialized in processing German banking documents.
        Your task is to analyze documents and provide structured JSON output with the following:

        1. Category classification (one of: loan_applications, account_inquiries, complaints, kyc_updates, general_correspondence)
        2. Urgency level (high, medium, low)
        3. Extract customer information (ID, account number, contact details)
        4. Identify required actions
        5. Provide confidence score (0-1)

        Consider German and English text. Look for keywords like:
        - Kredit/Darlehen (loan)
        - Konto (account)
        - Beschwerde (complaint)
        - Legitimation/KYC

        Return ONLY valid JSON in this format:
        {
            "category": "string",
            "urgency": "string",
            "metadata": {
                "customer_id": "string or null",
                "account_number": "string or null",
                "email": "string or null",
                "phone": "string or null",
                "subject": "string or null"
            },
            "extracted_info": {
                "required_action": "string",
                "key_points": ["list of strings"],
                "mentioned_amounts": "string or null",
                "reference_numbers": ["list of strings"]
            },
            "confidence_score": float
        }"""

    def _create_classification_prompt(self, text: str) -> str:
        return f"""Analyze this banking document and classify it according to the instructions:

        DOCUMENT TEXT:
        {text[:3000]}

        Provide the structured JSON response."""

    def _get_department(self, category: str) -> str:
        return settings.DEPARTMENT_EMAILS.get(category, "info@bank.de")