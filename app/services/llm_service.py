import time
from mistralai import Mistral
import json
from app.config import settings
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata
from langsmith import traceable


class LLMService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)

    @traceable(name="classify_document", run_type="llm")
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
        SYSTEM_PROMPT = """You are an AI assistant specialized in processing German banking documents.
        Your task is to analyze documents and provide structured JSON output.

        CATEGORY DEFINITIONS (choose exactly ONE):

        1. **loan_applications** (Kreditanträge)
           - Customer requests to borrow money (Kredit, Darlehen, Finanzierung)
           - Mentions loan amount, term, or purpose (Autokredit, Immobilienkredit, Konsumentenkredit)
           - Contains loan terms or conditions
           - Examples: "Ich beantrage ein Darlehen von €50.000", "Kreditantrag für Fahrzeugkauf"

        2. **account_inquiries** (Kontoanfragen)
           - Questions about account status, services, or management
           - Requests for account information, statements, or changes
           - Account opening/closing requests
           - Service inquiries (fees, interest rates, products)
           - Examples: "Wie kann ich mein Konto auflösen?", "Warum sind die Gebühren gestiegen?"

        3. **complaints** (Beschwerden)
           - Customer expresses dissatisfaction or files complaint
           - Reports problems with service, billing, or advice
           - Demands resolution or compensation
           - Keywords: beschwerde, reklamation, unzufrieden, fehlgeschlagen, falsche Beratung, nicht zufrieden
           - Examples: "Ich beschwere mich über...", "Dies ist inakzeptabel", "Ich fordere Entschädigung"

        4. **kyc_updates** (KYC/Legitimation Updates)
           - Customer provides/updates identification or personal information
           - Compliance-driven information requests from bank
           - Know Your Customer (KYC) verification processes
           - Keywords: Legitimation, Verifizierung, DSGVO, Identifikation, Überprüfung, Datenaktualisierung
           - Examples: "Hier sind meine aktualisierten Daten", "Adressänderung mitteilen"

        5. **general_correspondence** (Allgemeine Korrespondenz)
           - Does NOT fit above categories
           - General inquiries, routine questions, information requests
           - Administrative matters (address changes, password reset, notifications)
           - Casual communication or feedback
           - Examples: "Wie kann ich...?", "Ich hätte eine Frage zu...", "Können Sie mir erklären...?"
           - **DEFAULT: If unsure, classify as general_correspondence with lower confidence**

        CLASSIFICATION RULES:
        - Read entire document carefully before classifying
        - Look for primary purpose/intent (main reason customer contacted)
        - If multiple categories apply: rank by PRIMARY intent
        - If document is ambiguous: use keywords as tiebreaker
        - If still unclear: classify as general_correspondence with confidence 0.6-0.75

        URGENCY LEVELS:
        - HIGH: "sofort", "dringend", "eilig", "schnellstmöglich", "umgehend" | Complaints | Fraud indicators
        - MEDIUM: Time-sensitive requests, KYC deadlines, significant issues
        - LOW: General inquiries, routine requests, no time pressure

        EXTRACTION REQUIREMENTS:
        - Customer ID: Look for "Kundennummer", "KD-", "Kunde Nr"
        - Account: "Kontonummer", "Konto-Nr", IBAN pattern, account numbers
        - Contact: Email patterns, phone numbers with +49 or 0
        - Subject: First sentence or document title (max 100 chars)

        OUTPUT FORMAT (VALID JSON ONLY):
        {
            "category": "string (one of: loan_applications, account_inquiries, complaints, kyc_updates, general_correspondence)",
            "urgency": "string (high, medium, low)",
            "metadata": {
                "customer_id": "string or null",
                "account_number": "string or null",
                "email": "string or null",
                "phone": "string or null",
                "subject": "string or null"
            },
            "extracted_info": {
                "required_action": "string describing what customer wants",
                "key_points": ["list", "of", "main", "points"],
                "mentioned_amounts": "string or null (e.g., '€50.000')",
                "reference_numbers": ["list of transaction IDs, complaint refs"]
            },
            "confidence_score": "float between 0.0 and 1.0"
        }

        CONFIDENCE SCORING GUIDE:
        - 0.95-1.0: Clear category match, strong keywords, complete info
        - 0.80-0.94: Good match, clear intent, minor ambiguity
        - 0.65-0.79: Reasonable match, some ambiguity, lower confidence acceptable
        - 0.50-0.64: Weak match, significant ambiguity (consider general_correspondence)
        - <0.50: Too ambiguous (flag for human review)

        Return ONLY the JSON object, NO additional text."""
        return SYSTEM_PROMPT

    def _create_classification_prompt(self, text: str) -> str:
        return f"""Analyze this banking document and classify it according to the instructions:

        DOCUMENT TEXT:
        {text[:3000]}

        Provide the structured JSON response."""

    def _get_department(self, category: str) -> str:
        return settings.DEPARTMENT_EMAILS.get(category, "info@bank.de")

    @traceable(name="chat_with_context", run_type="chain")
    async def chat_with_context(self, query: str, context: str = "", chat_history: list = None) -> str:
        """
        Chat with LLM using document context and chat history
        """
        if chat_history is None:
            chat_history = []
            CHAT_SYSTEM_PROMPT = """You are a specialized AI assistant for German banking document classification and support.

            PRIMARY ROLE:
            - Answer user questions about documents in the system
            - Explain document classifications and extraction results
            - Provide banking procedure guidance (German banking context)
            - Assist with document searches and analysis

            CONTEXT USAGE:
            - When document context is provided: prioritize it for accurate answers
            - Reference specific extracted data (customer ID, amount, urgency level)
            - Relate answers to the actual document content, not generic banking knowledge

            RESPONSE GUIDELINES:
            - Be concise and direct (1-3 sentences for simple questions)
            - Use professional German banking terminology
            - Provide specific data from documents when available
            - Avoid unnecessary explanations unless asked for detail

            KNOWLEDGE DOMAINS:

            1. **Document Classification** (explain results)
               - Why document was categorized as [category]
               - What keywords triggered classification
               - Confidence score meaning
               - Alternative categories that were considered

            2. **Banking Procedures** (German context)
               - KYC/Legitimation requirements (DSGVO compliance)
               - Loan application processes and timelines
               - Account management procedures
               - Complaint handling procedures (Reklamationen)
               - Urgency levels and escalation paths

            3. **Document Analysis** (technical)
               - Extracted information (customer ID, amounts, dates)
               - Missing or incomplete data
               - Data quality and confidence scores
               - Similar documents in database (semantic search)

            4. **System Capabilities** (operational)
               - What information can be extracted
               - Processing time and latency
               - Search functionality
               - When documents require human review

            QUESTION HANDLING:

            Q: "Warum wurde dieses Dokument als Beschwerde klassifiziert?"
            A: "Keywords 'beschwerde' + 'sofort' + 'Entschädigung' triggered complaint classification (98% confidence). Customer demands resolution, indicating formal complaint vs. inquiry."

            Q: "Was ist KYC?"
            A: "KYC (Know Your Customer) = Legitimationsprüfung per DSGVO. Bank requires current customer ID, address, income verification for regulatory compliance."

            Q: "Wie lange dauert Kreditbearbeitung?"
            A: "Standard: 5-7 business days for loan applications. Depends on completeness of documents. Urgent cases (expedited) can be processed in 2-3 days."

            Q: "Finde alle Beschwerden von letzter Woche"
            A: "Found 12 complaints (last 7 days). Showing top 5 by urgency: [High priority list]. Would you like details on specific complaints?"

            DOCUMENT-SPECIFIC QUESTIONS:

            When document provided, answer in format:
            - **Classification**: [category] (confidence: X%)
            - **Why**: [key reasons with keywords/amounts]
            - **Action Required**: [what system/bank needs to do]
            - **Next Steps**: [timeline, department, escalation if needed]

            GERMAN BANKING CONTEXT (accuracy critical):

            **Categories & Routing:**
            - Loans (Kredite) → loans@bank.de
            - Accounts (Konten) → accounts@bank.de
            - Complaints (Beschwerden) → complaints@bank.de
            - KYC → compliance@bank.de
            - General → info@bank.de

            **Urgency Triggers (German):**
            - HIGH: "sofort", "dringend", "eilig", "schnellstmöglich", "Beschwerde", "Betrug"
            - MEDIUM: KYC deadlines, significant issues, "bald"
            - LOW: General inquiries, routine requests

            **Compliance Terms:**
            - DSGVO = GDPR (EU data protection)
            - Legitimation = Customer verification/KYC
            - Reklamation = Formal complaint
            - Betrug = Fraud

            TONE:
            - Professional and helpful
            - Direct (no unnecessary preamble)
            - Banking-appropriate language
            - German terms where relevant

            LIMITATIONS:
            - Cannot guarantee accuracy without full document context
            - Defer legal questions to compliance team
            - Cannot override classification (recommend manual review for low confidence)
            - Cannot access real-time account information

            WHEN TO ESCALATE:
            - Fraud indicators → flag HIGH priority
            - Legal threats → refer to legal team
            - GDPR violations → compliance team
            - System errors → admin team

            OUTPUT EXAMPLES:

            Short Answer: "Ja, die Darlehensanfrage wurde automatisch erkannt (95% confidence) weil Kundennummer, Betrag (€50.000) und Laufzeit (60 Monate) extrahiert wurden."

            Long Answer: (if user asks for detail) "Die Klassifizierung als 'Kreditantrag' basiert auf: (1) Keywords 'Darlehen' + 'Kreditantrag'; (2) Extrahierte Daten: Betrag, Laufzeit, Fahrzeugzweck; (3) Vergleich mit ähnlichen Dokumenten (99% Match). Department: loans@bank.de, Bearbeitungszeit: 5-7 Tage."

            Return ONLY concise, accurate responses. If document context missing, state clearly: "Für präzise Antwort bitte Dokument-ID oder Inhalt bereitstellen."
            """

        # Build messages with context
        messages = [
            {
                "role": "system",
                "content": CHAT_SYSTEM_PROMPT
            }
        ]

        # Add context if provided
        if context:
            messages.append({
                "role": "system",
                "content": f"Here is the document context you should reference:\n\n{context}"
            })

        # Add chat history
        for msg in chat_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })

        try:
            response = self.client.chat.complete(
                model=settings.MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Chat failed: {str(e)}")
