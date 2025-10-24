# 🏦 Bank Document Classification System

An AI-powered document processing system for German banking institutions, leveraging Mistral AI for intelligent document classification, information extraction, and automated routing with GDPR/DSGVO compliance.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Mistral AI](https://img.shields.io/badge/Mistral-AI-orange.svg)](https://mistral.ai/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-purple.svg)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Web UI Features](#web-ui-features)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This system automates the entire document processing workflow for German banks:

1. **Ingest & Digitize**: Automatically collect and process documents from emails, uploads, and scanned files
2. **OCR Processing**: Extract text and structural data using Mistral Document AI
3. **Classify & Extract**: Analyze content with Mistral LLM to categorize documents and extract key information
4. **Store & Index**: Convert documents to embeddings and store in a vector database for semantic search
5. **Route & Alert**: Automatically route documents to appropriate departments with priority-based alerts

### Document Categories

- 💳 **Loan Applications** (Kreditanträge)
- 💰 **Account Inquiries** (Kontoanfragen)
- ⚠️ **Complaints** (Beschwerden)
- 🔐 **KYC Updates** (Legitimation Updates)
- 📄 **General Correspondence** (Allgemeine Korrespondenz)

## ✨ Features

### Core Capabilities

- ✅ **Multi-format OCR**: Process PDFs, images, and text documents with Mistral OCR
- ✅ **Intelligent Classification**: Automatic categorization of German banking documents
- ✅ **Information Extraction**: Extract customer IDs, account numbers, urgency levels, and key details
- ✅ **GDPR Compliance**: Built-in DSGVO compliance checks and data privacy controls
- ✅ **Semantic Search**: Vector-based document search using embeddings
- ✅ **Smart Routing**: Automatic department assignment based on document type
- ✅ **Priority Alerts**: Flag high-urgency documents for immediate attention
- ✅ **Model Rotation**: Automatic fallback to alternative models on rate limits
- ✅ **Interactive Chatbot**: AI assistant for general queries and document-specific Q&A

### Web Interface

- 📤 **Document Upload**: Drag-and-drop interface for file uploads
- 📋 **Category View**: Documents organized by category with count badges
- 🔍 **Semantic Search**: Natural language search across all documents
- 💬 **AI Chatbot**: Interactive assistant for banking queries
- 📄 **Document Details**: Detailed view with metadata and document-specific chat
- 🎨 **Responsive Design**: Modern, mobile-friendly UI

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (Web UI)   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
├─────────────────────────────────────┤
│  • Document Upload                  │
│  • Text Processing                  │
│  • Search & Retrieval               │
│  • Chatbot Interface                │
└──────┬────────────┬─────────────────┘
       │            │
       ▼            ▼
┌─────────────┐  ┌──────────────┐
│  Mistral AI │  │  ChromaDB    │
├─────────────┤  ├──────────────┤
│ • OCR       │  │ • Vector DB  │
│ • LLM       │  │ • Embeddings │
│ • Chat      │  │ • Metadata   │
└─────────────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│       Routing Service               │
├─────────────────────────────────────┤
│  • Department Assignment            │
│  • Priority Alerts                  │
│  • Notifications                    │
└─────────────────────────────────────┘
```

## 🛠️ Tech Stack

### Backend & API
- **Python 3.11**: Core programming language
- **FastAPI**: Modern, high-performance web framework
- **Uvicorn**: ASGI server for production deployment

### AI & Machine Learning
- **Mistral AI**: 
  - OCR: `mistral-ocr-2505` for document text extraction
  - LLM: `mistral-medium-2508` for classification and extraction
  - Embeddings: `mistral-embed` for semantic search
  - Chat: Interactive AI assistant
- **LangChain**: Framework for LLM applications
- **LangSmith**: Tracing and monitoring (optional)

### Database & Storage
- **ChromaDB**: Vector database for embeddings and semantic search
- **Persistent Storage**: Docker volumes for data persistence

### Deployment
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

### Testing
- **Pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage reporting
- **pytest-mock**: Mocking utilities
- **Faker**: Test data generation

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Mistral AI API key ([Get one here](https://console.mistral.ai/))
- macOS, Linux, or Windows with WSL2

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd GenAI_Document_Classification
```

2. **Create `.env` file**
```bash
echo "MISTRAL_API_KEY=your_api_key_here" > .env
```

3. **Start the system** (One-command setup!)
```bash
./run.sh
```

### Alternative: Manual Start

```bash
# Build and start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Access Points

Once running:

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | http://localhost:8000 | Main web application |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **ChromaDB** | http://localhost:8001 | Vector database admin |

## 📁 Project Structure

```
GenAI_Document_Classification/
├── app/
│   ├── main.py                 # FastAPI application & routes
│   ├── config.py               # Configuration & settings
│   ├── constants.py            # System prompts & constants
│   ├── database/
│   │   ├── chroma_client.py    # ChromaDB client
│   │   └── chromadb_cloud_service.py  # Cloud service support
│   ├── models/
│   │   └── document.py         # Pydantic models & schemas
│   ├── services/
│   │   ├── ocr_service.py      # Mistral OCR integration
│   │   ├── llm_service.py      # LLM classification & extraction
│   │   ├── embedding_service.py # Document embeddings
│   │   ├── routing_service.py  # Department routing & alerts
│   │   └── model_rotation_service.py  # Fallback model handling
│   └── static/
│       ├── index.html          # Main web interface
│       ├── document-detail.html # Document detail page
│       ├── app.js              # Frontend JavaScript
│       └── style.css           # Styling
├── tests/
│   ├── test_*.py               # Comprehensive test suite (100+ tests)
│   ├── conftest.py             # Pytest configuration
│   └── run_tests.sh            # Test runner script
├── docker-compose.yaml         # Docker orchestration
├── Dockerfile                  # Application container
├── requirements.txt            # Python dependencies
├── run.sh                      # Quick start script
└── README.md                   # This file
```

## 📚 API Documentation

### Core Endpoints

#### 1. Process Document
```http
POST /process-document
Content-Type: multipart/form-data

file: <document file>
```

**Supported formats**: PDF, PNG, JPG, JPEG, TXT

**Response**:
```json
{
  "document_id": "uuid",
  "category": "loan_applications",
  "urgency_level": "high",
  "metadata": {
    "customer_id": "KD-123456789",
    "account_number": "DE89370400440532013000"
  },
  "extracted_info": {},
  "routing": {}
}
```

#### 2. Process Text
```http
POST /process-text
Content-Type: application/json

{
  "text": "Document content",
  "filename": "optional_name.txt"
}
```

#### 3. Search Documents
```http
GET /search-documents?query=Kredit&n_results=5
```

Semantic search using vector embeddings.

#### 4. Get Documents by Category
```http
GET /documents-by-category
```

Returns all documents grouped by category.

#### 5. Get Document Details
```http
GET /document/{document_id}
```

#### 6. AI Chatbot
```http
POST /chat
Content-Type: application/json

{
  "query": "Wie beantrage ich einen Kredit?",
  "chat_history": [],
  "document_id": "optional-uuid"
}
```

#### 7. Health Check
```http
GET /api/health
```

### Interactive Documentation

Visit http://localhost:8000/docs for full interactive API documentation with **Try it out** functionality.

## 🖥️ Web UI Features

### Main Dashboard

1. **Document Upload Section**
   - Drag-and-drop file upload
   - Support for PDF, images, and text files
   - Real-time processing status
   - Detailed result display with JSON formatting

2. **Documents by Category**
   - Organized view with category headers
   - Document count badges
   - Urgency level indicators (🔴 High, 🟡 Medium, 🟢 Low)
   - Clickable cards for document details
   - Auto-refresh after upload

3. **AI Chatbot**
   - Natural language banking queries
   - Context-aware responses
   - Chat history maintained
   - Markdown formatting support

### Document Detail Page

- Full document metadata display
- Customer information panel
- GDPR compliance status
- Document-specific chatbot for Q&A
- Back to main page navigation

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Mistral AI Configuration
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-medium-2508
MISTRAL_EMBEDDING_MODEL=mistral-embed
MISTRAL_OCR_MODEL=mistral-ocr-2505

# ChromaDB Configuration
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=bank_documents
```

### Model Configuration

The system supports automatic model rotation when rate limits are hit:

**Primary Models**:
- Classification: `mistral-medium-2508`
- OCR: `mistral-ocr-2505`
- Embeddings: `mistral-embed`

**Fallback Models**:
- `mistral-small-latest`
- `mistral-large-latest`
- `mistral-medium-latest`
- `magistral-medium-2509`
- `ministral-3b-2410`

### Department Routing

Configure department email addresses in `app/config.py`:

```python
DEPARTMENT_EMAILS = {
    "loan_applications": "loans@bank.de",
    "account_inquiries": "accounts@bank.de",
    "complaints": "complaints@bank.de",
    "kyc_updates": "compliance@bank.de",
    "general_correspondence": "info@bank.de"
}
```

### Urgency Keywords

Customize urgency detection in `app/config.py`:

```python
HIGH_URGENCY_KEYWORDS = [
    # English
    "urgent", "immediate", "asap", "critical", "emergency",
    # German
    "dringend", "sofort", "unverzüglich", "eilig", "schnellstmöglich"
]
```

## 🧪 Testing

### Run All Tests

```bash
# Using the test script (recommended)
cd tests
./run_tests.sh

# Or using pytest directly
pytest

# With coverage report
pytest --cov=app --cov-report=html --cov-report=term
```
```bash
# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow          # Long-running tests

# Run specific test files
pytest tests/test_api.py
pytest tests/test_llm_service.py
```


## 🐳 Deployment

### Docker Compose (Recommended)

The system uses Docker Compose for easy deployment:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
    depends_on:
      - chromadb

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
```

### Cloud Deployment

The project includes cloud-ready configurations:

- `docker-composer-cloud-service.yaml`: Cloud service configuration
- `app/main-chromadb-cloud.py`: Cloud ChromaDB integration

## 🔒 GDPR/DSGVO Compliance

The system includes built-in GDPR compliance features:

- ✅ Data minimization principles
- ✅ Purpose limitation checks
- ✅ Consent validation
- ✅ Right to deletion support
- ✅ Data retention policies
- ✅ Compliance flags in document metadata
- ✅ Audit trail for data processing

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock faker

# Run tests before committing
pytest
```

## 🐛 Troubleshooting

### Common Issues

1. **Docker not running**
   ```bash
   # Start Docker Desktop or Docker daemon
   # Then retry: ./run.sh
   ```

2. **Port already in use**
   ```bash
   # Stop conflicting services
   docker compose down
   # Or change ports in docker-compose.yaml
   ```

3. **Mistral API rate limits**
   - The system automatically rotates through fallback models
   - Check your API quota at https://console.mistral.ai/

4. **ChromaDB connection issues**
   ```bash
   # Restart ChromaDB
   docker compose restart chromadb
   ```

## 📝 License

This project is proprietary software. All rights reserved.

## 👥 Authors

- **Mahshid Ahmadi** -

## 🙏 Acknowledgments

- **Mistral AI** for powerful LLM and OCR capabilities
- **ChromaDB** for efficient vector storage
- **FastAPI** for excellent API framework
- **Docker** for containerization



