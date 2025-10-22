import time
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import MistralClient as Mistral
import json
import logging
from app.config import settings
from app.models.document import DocumentCategory, UrgencyLevel, ProcessedDocument, DocumentMetadata, GDPRCompliance
from app.services.model_rotation_service import ModelRotationService
from app.constants import SYSTEM_PROMPT_GERMAN_GDPR
from langsmith import traceable

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
        # Initialize model rotation service
        self.model_rotator = ModelRotationService(settings.MISTRAL_FALLBACK_MODELS)
        self.current_model = settings.MISTRAL_MODEL
        self.system_prompt = SYSTEM_PROMPT_GERMAN_GDPR

    @traceable(name="classify_document", run_type="llm")
    async def classify_and_extract(self, text: str) -> ProcessedDocument:
        """
        Use Mistral LLM to classify document and extract key information
        Automatically rotates through fallback models if rate limits are hit
        """
        prompt = self._create_classification_prompt(text)
        max_model_attempts = len(settings.MISTRAL_FALLBACK_MODELS)
        error_str = "Unknown error"  # Initialize to avoid reference before assignment

        for model_attempt in range(max_model_attempts):
            # Get next available model
            if model_attempt == 0:
                model_to_use = self.current_model
            else:
                model_to_use = self.model_rotator.get_next_available_model(self.current_model)
                self.current_model = model_to_use
                logger.info(f"Switching to fallback model: {model_to_use}")

            max_retries = 2  # Reduced retries per model since we have multiple models

            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting classification with model: {model_to_use} (attempt {attempt + 1}/{max_retries})")

                    response = self.client.chat.complete(
                        model=model_to_use,
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

                    # Create a ProcessedDocument with safe access to optional fields
                    gdpr_data = result.get("gdpr_compliance", {})

                    # Safely create GDPRCompliance object with defaults
                    try:
                        gdpr_info = GDPRCompliance(**gdpr_data) if gdpr_data else GDPRCompliance()
                    except Exception as gdpr_error:
                        logger.warning(f"Failed to parse GDPR data: {gdpr_error}, using defaults")
                        gdpr_info = GDPRCompliance()

                    processed_doc = ProcessedDocument(
                        raw_text=text,
                        category=DocumentCategory(result.get("category", "general_correspondence")),
                        urgency_level=UrgencyLevel(result.get("urgency", "medium")),
                        metadata=DocumentMetadata(**result.get("metadata", {})),
                        extracted_info=result.get("extracted_info", {}),
                        confidence_score=result.get("confidence_score", 0.5),
                        assigned_department=self._get_department(result.get("category", "general_correspondence")),
                        requires_immediate_attention=(result.get("urgency") == "high"),
                        gdpr_info=gdpr_info
                    )

                    # Mark success
                    self.model_rotator.mark_success(model_to_use)
                    logger.info(f"Successfully classified document with model: {model_to_use}")

                    return processed_doc

                except Exception as e:
                    error_str = str(e)

                    # Check if it's a rate limit error
                    if "429" in error_str or "rate_limit" in error_str.lower() or "quota" in error_str.lower():
                        logger.warning(f"Rate limit hit for model {model_to_use}: {error_str}")
                        self.model_rotator.mark_rate_limited(model_to_use)
                        break  # Break retry loop and try next model

                    # For other errors, retry with exponential backoff
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        logger.warning(f"Error with {model_to_use}, retrying in {wait}s: {error_str}")
                        time.sleep(wait)
                    else:
                        logger.error(f"Failed all retries for model {model_to_use}: {error_str}")
                        break  # Try next model

        # If we've exhausted all models
        raise Exception(f"LLM classification failed after trying all available models. Last error: {error_str if 'error_str' in locals() else 'Unknown'}")

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT_GERMAN_GDPR

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

        # Define system prompt in German
        CHAT_SYSTEM_PROMPT = """Du bist ein spezialisierter KI-Assistent für deutsche Bankdokumentenklassifizierung und -unterstützung.

HAUPTAUFGABE:
- Beantworte Benutzerfragen zu Dokumenten im System
- Erkläre Dokumentklassifizierungen und Extraktionsergebnisse
- Biete Anleitung zu Bankverfahren (deutscher Bankkontext)
- Unterstütze bei Dokumentensuchen und -analysen

WICHTIG: Antworte IMMER auf Deutsch, auch wenn die Frage auf Englisch gestellt wird.

KONTEXTNUTZUNG:
- Wenn Dokumentkontext bereitgestellt wird: priorisiere ihn für genaue Antworten
- Beziehe dich auf spezifische extrahierte Daten (Kundennummer, Betrag, Dringlichkeitsstufe)
- Verknüpfe Antworten mit dem tatsächlichen Dokumentinhalt, nicht mit allgemeinem Bankwissen

ANTWORTRICHTLINIEN:
- Sei prägnant und direkt (1-3 Sätze für einfache Fragen)
- Verwende professionelle deutsche Bankterminologie
- Liefere spezifische Daten aus Dokumenten, wenn verfügbar
- Vermeide unnötige Erklärungen, es sei denn, nach Details gefragt

WISSENSBEREICHE:

1. **Dokumentklassifizierung** (Ergebnisse erklären)
   - Warum wurde das Dokument als [Kategorie] eingestuft
   - Welche Schlüsselwörter lösten die Klassifizierung aus
   - Bedeutung des Vertrauenswerts
   - Alternative Kategorien, die in Betracht gezogen wurden

2. **Bankverfahren** (deutscher Kontext)
   - KYC/Legitimationsanforderungen (DSGVO-Konformität)
   - Kreditantragsprozesse und Zeitpläne
   - Kontoverwaltungsverfahren
   - Beschwerdeverfahren (Reklamationen)
   - Dringlichkeitsstufen und Eskalationswege

3. **Dokumentanalyse** (technisch)
   - Extrahierte Informationen (Kundennummer, Beträge, Daten)
   - Fehlende oder unvollständige Daten
   - Datenqualität und Vertrauenswerte
   - Ähnliche Dokumente in der Datenbank (semantische Suche)

4. **Systemfähigkeiten** (betrieblich)
   - Welche Informationen extrahiert werden können
   - Verarbeitungszeit und Latenz
   - Suchfunktionalität
   - Wann Dokumente menschliche Überprüfung erfordern

FRAGENBEHANDLUNG:

F: "Warum wurde dieses Dokument als Beschwerde klassifiziert?"
A: "Schlüsselwörter 'beschwerde' + 'sofort' + 'Entschädigung' lösten Beschwerdeklassifizierung aus (98% Vertrauen). Kunde fordert Lösung, was auf formelle Beschwerde vs. Anfrage hinweist."

F: "Was ist KYC?"
A: "KYC (Know Your Customer) = Legitimationsprüfung per DSGVO. Bank benötigt aktuelle Kundennummer, Adresse, Einkommensnachweis für regulatorische Konformität."

F: "Wie lange dauert Kreditbearbeitung?"
A: "Standard: 5-7 Werktage für Kreditanträge. Abhängig von Vollständigkeit der Dokumente. Dringende Fälle können in 2-3 Tagen bearbeitet werden."

F: "Finde alle Beschwerden von letzter Woche"
A: "12 Beschwerden gefunden (letzte 7 Tage). Zeige Top 5 nach Dringlichkeit: [High-Priority-Liste]. Möchten Sie Details zu bestimmten Beschwerden?"

TON:
- Professionell und hilfsbereit
- Direkt (keine unnötige Einleitung)
- Bankangemessene Sprache
- Deutsche Begriffe durchgehend

EINSCHRÄNKUNGEN:
- Kann Genauigkeit ohne vollständigen Dokumentkontext nicht garantieren
- Rechtsfragen an Compliance-Team weiterleiten
- Kann Klassifizierung nicht überschreiben (manuelle Überprüfung bei niedrigem Vertrauen empfehlen)
- Kann nicht auf Echtzeitkontoinformationen zugreifen

WANN ESKALIEREN:
- Betrugshinweise → HIGH-Priorität markieren
- Rechtliche Drohungen → an Rechtsabteilung weiterleiten
- DSGVO-Verstöße → Compliance-Team
- Systemfehler → Admin-Team

Gib NUR prägnante, genaue Antworten auf Deutsch zurück. Wenn Dokumentkontext fehlt, sage klar: "Für präzise Antwort bitte Dokument-ID oder Inhalt bereitstellen."
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
                "content": f"Hier ist der Dokumentkontext, auf den du dich beziehen solltest:\n\n{context}"
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
                model=self.current_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"Chat failed: {str(e)}")
