import base64
import re
from typing import Union, Dict, List, Optional
from dataclasses import dataclass
from mistralai import Mistral
from app.config import settings


@dataclass
class DocumentStructure:
    """Structured representation of document extracted by Mistral OCR"""
    raw_text: str
    pages: List[Dict]
    tables: List[Dict]
    forms: Dict[str, str]
    metadata: Dict
    model: str
    usage_info: Dict


class MistralOCRService:
    """
    OCR service using Mistral OCR API for intelligent document processing
    """

    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.model = "mistral-ocr-latest"

    def process_document(
            self,
            document: Union[bytes, str],
            document_type: str = "pdf",
            include_images: bool = True,
            pages: Optional[List[int]] = None
    ) -> DocumentStructure:
        """
        Process document using Mistral OCR API

        Args:
            document: Document bytes or base64 string
            document_type: Type of document (pdf, png, jpeg, etc.)
            include_images: Whether to include base64 images in response
            pages: Optional list of specific page indices to process

        Returns:
            DocumentStructure with extracted content
        """
        try:
            # For text files, create a simple structure without OCR
            if document_type in ['txt', 'text']:
                if isinstance(document, bytes):
                    text_content = document.decode('utf-8')
                else:
                    text_content = document

                return DocumentStructure(
                    raw_text=text_content,
                    pages=[{"index": 0, "markdown": text_content, "images": [], "dimensions": {}}],
                    tables=[],
                    forms={},
                    metadata={"document_type": "text", "language": "de"},
                    model="text-passthrough",
                    usage_info={"pages_processed": 1, "doc_size_bytes": len(text_content)}
                )

            # Prepare document for processing
            if isinstance(document, bytes):
                document_b64 = base64.b64encode(document).decode('utf-8')
            else:
                document_b64 = document

            # Construct data URI for base64 document
            mime_type = self._get_mime_type(document_type)
            document_url = f"data:{mime_type};base64,{document_b64}"

            # Call Mistral OCR API using the client
            ocr_response = self.client.ocr.process(
                model=self.model,
                document={
                    "type": "document_url",
                    "document_url": document_url
                },
                include_image_base64=include_images,
                pages=pages
            )

            # Parse the response
            document_structure = self._parse_ocr_response(ocr_response)

            # Enhance with banking-specific context
            document_structure = self._enhance_banking_context(document_structure)

            return document_structure

        except Exception as e:
            raise Exception(f"Mistral OCR API error: {str(e)}")

    def _get_mime_type(self, document_type: str) -> str:
        """Map document type to MIME type"""
        mime_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "avif": "image/avif"
        }
        return mime_types.get(document_type.lower(), "application/pdf")

    def _parse_ocr_response(self, response) -> DocumentStructure:
        """
        Parse the Mistral OCR API response

        Response structure:
        {
            "pages": [
                {
                    "index": 0,
                    "markdown": "text content...",
                    "images": [
                        {
                            "id": "img-1.png",
                            "top_left_x": 100,
                            "top_left_y": 50,
                            "bottom_right_x": 400,
                            "bottom_right_y": 300,
                            "image_base64": "..."
                        }
                    ],
                    "dimensions": {
                        "dpi": 200,
                        "height": 1000,
                        "width": 800
                    }
                }
            ],
            "model": "mistral-ocr-latest",
            "usage_info": {
                "pages_processed": 1,
                "doc_size_bytes": 123456
            }
        }
        """
        # Combine all page markdown into raw text
        raw_text = ""
        pages = []

        for page in response.pages:
            raw_text += page.markdown + "\n\n"
            pages.append({
                "index": page.index,
                "markdown": page.markdown,
                "images": [
                    {
                        "id": img.id,
                        "bbox": {
                            "top_left": (img.top_left_x, img.top_left_y),
                            "bottom_right": (img.bottom_right_x, img.bottom_right_y)
                        },
                        "image_base64": getattr(img, 'image_base64', None)
                    }
                    for img in page.images
                ] if hasattr(page, 'images') else [],
                "dimensions": {
                    "dpi": page.dimensions.dpi,
                    "height": page.dimensions.height,
                    "width": page.dimensions.width
                } if hasattr(page, 'dimensions') else {}
            })

        # Extract tables from markdown
        tables = self._extract_tables_from_markdown(raw_text)

        # Initialize empty forms dict (will be populated by banking enhancement)
        forms = {}

        # Metadata
        metadata = {
            "model": response.model,
            "pages_processed": response.usage_info.pages_processed,
            "doc_size_bytes": response.usage_info.doc_size_bytes
        }

        return DocumentStructure(
            raw_text=raw_text.strip(),
            pages=pages,
            tables=tables,
            forms=forms,
            metadata=metadata,
            model=response.model,
            usage_info={
                "pages_processed": response.usage_info.pages_processed,
                "doc_size_bytes": response.usage_info.doc_size_bytes
            }
        )

    def _extract_tables_from_markdown(self, markdown: str) -> List[Dict]:
        """Extract tables from markdown format"""
        tables = []
        lines = markdown.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a table row (contains |)
            if '|' in line and line.startswith('|'):
                table_lines = [line]
                i += 1

                # Collect all consecutive table lines
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1

                # Parse the table
                if len(table_lines) >= 2:  # Need at least header and separator
                    headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
                    rows = []

                    # Skip separator line (usually index 1)
                    for row_line in table_lines[2:]:
                        cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
                        if cells:
                            rows.append(cells)

                    if headers and rows:
                        tables.append({
                            "headers": headers,
                            "rows": rows
                        })
            else:
                i += 1

        return tables

    def _enhance_banking_context(self, structure: DocumentStructure) -> DocumentStructure:
        """
        Enhance extraction with banking-specific field recognition
        """
        # Banking-specific field mappings (German and English)
        banking_patterns = {
            "iban": r'[A-Z]{2}\d{2}\s?(?:\w{4}\s?){2,7}\w{1,4}',
            "customer_id": [
                r'(?:Kundennummer|Customer\s*ID|Kunden-Nr|KD-Nr)[:\s]+([A-Z0-9]{6,12})',
                r'(?:Kunde|Customer)[:\s]+(\d{8,12})',
                r'KN[:\s]+([A-Z0-9]{6,12})'
            ],
            "account_number": r'(?:Kontonummer|Account\s*Number)[:\s]+([A-Z0-9]{6,20})',
            "bic": r'(?:BIC|SWIFT)[:\s]+([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)',
            "date": r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}',
            "amount": r'€?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\s*€?'
        }

        forms = {}
        text = structure.raw_text

        # Extract IBAN
        iban_match = re.search(banking_patterns["iban"], text.upper())
        if iban_match:
            forms["iban"] = iban_match.group(0).replace(" ", "")

        # Extract customer ID
        for pattern in banking_patterns["customer_id"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                forms["customer_id"] = match.group(1)
                break

        # Extract account number
        account_match = re.search(banking_patterns["account_number"], text, re.IGNORECASE)
        if account_match:
            forms["account_number"] = account_match.group(1)

        # Extract BIC
        bic_match = re.search(banking_patterns["bic"], text, re.IGNORECASE)
        if bic_match:
            forms["bic"] = bic_match.group(1)

        structure.forms = forms
        return structure

    def format_for_downstream(self, structure: DocumentStructure) -> str:
        """
        Format the structured document for downstream LLM processing
        """
        formatted = []

        # Add extracted text
        formatted.append("=== DOCUMENT TEXT ===")
        formatted.append(structure.raw_text)
        formatted.append("")

        # Add extracted fields if present
        if structure.forms:
            formatted.append("=== EXTRACTED FIELDS ===")
            for field, value in structure.forms.items():
                formatted.append(f"{field}: {value}")
            formatted.append("")

        # Add tables if present
        if structure.tables:
            formatted.append("=== TABLES ===")
            for i, table in enumerate(structure.tables, 1):
                formatted.append(f"Table {i}:")
                if table.get("headers"):
                    formatted.append("Headers: " + " | ".join(table["headers"]))
                for row in table.get("rows", []):
                    formatted.append(" | ".join(str(cell) for cell in row))
                formatted.append("")

        # Add metadata
        formatted.append("=== METADATA ===")
        formatted.append(f"Model: {structure.model}")
        formatted.append(f"Pages Processed: {structure.usage_info['pages_processed']}")
        formatted.append(f"Document Size: {structure.usage_info['doc_size_bytes']} bytes")

        return "\n".join(formatted)