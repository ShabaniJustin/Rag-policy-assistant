# RAG Policy Assistant

A Retrieval-Augmented Generation (RAG) chatbot for querying PDF documents using natural language. Upload any PDF document, and the application will process it, create vector embeddings, store them in Pinecone, and use a local LLM via Ollama to provide accurate, context-aware responses.

## Features

- **Dynamic PDF Upload**: Upload any PDF file through the web interface
- **Semantic Search**: Uses vector embeddings for context-aware document retrieval
- **Local LLM Integration**: Generates responses using Ollama (Gemma model)
- **Two Frontend Options**: Choose between Flask or Streamlit
- **Session-based Namespaces**: Each user session gets isolated document storage
- **REST API**: Simple API endpoints for integration with other applications

## Architecture

### Document Ingestion Pipeline

```
PDF Upload → PDF Reader → Chunker → Embedder → Pinecone
```

### Query Processing Pipeline with Guardrails

```
                        ┌─────────────────────┐
                        │      User Query      │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     G1 — Input Guardrail     │ ──► Blocked
                    │  Keyword filter · length     │
                    │  check · topic relevance     │
                    └──────────────┬──────────────┘
                                   │
          ┌────────────────────────▼────────────────────────┐
          │             RAG Pipeline (existing)              │
          │                                                  │
          │  Embed query → Pinecone search                   │
          │                        │                         │
          │           ┌────────────▼────────────┐            │
          │           │  G2 — Context Check     │            │
          │           │  Confidence score ·     │            │
          │           │  fallback               │            │
          │           └────────────┬────────────┘            │
          │                        │                         │
          │                  LLM (Gemma)                     │
          └────────────────────────┬────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    G3 — Output Guardrail     │ ──► Flagged
                    │  Hallucination check ·       │
                    │  PII scrub · length trim     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    G4 — Observability Log    │
                    │  Query · score · action ·    │
                    │  timestamp → guardrail.jsonl │
                    └──────────────┬──────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Safe Response to   │
                        │       User          │
                        └─────────────────────┘
```

## Guardrail System

The assistant uses 4 guardrail layers implemented in `guardrails.py` — pure Python, no external guardrail frameworks required.

### G1 — Input Guardrail
Validates every user query **before** it enters the RAG pipeline.

| Check | Detail |
|---|---|
| Empty query | Rejects blank input |
| Length limit | Max 500 characters |
| Prompt injection | Blocks patterns like `ignore previous instructions`, `act as`, `jailbreak` |
| Sensitive keywords | Blocks off-topic queries containing `password`, `hack`, `credit card`, `ssn`, etc. |

Also applied to `/api/upload`: rejects files larger than **10 MB**.

### G2 — Context Confidence Guardrail
Runs **inside `llm.py`** between Pinecone search and the LLM call. Prevents the LLM from being called with irrelevant or empty context.

| Check | Detail |
|---|---|
| No chunks returned | Rejects if Pinecone returns nothing |
| Low similarity score | Rejects if top chunk score < `0.5` (cosine similarity) |

> Without G2, Pinecone always returns the closest vectors it has — even for completely unrelated queries. The LLM has no access to the similarity score and may hallucinate a confident-sounding answer from irrelevant context. G2 catches this before the LLM is ever called.

### G3 — Output Guardrail
Validates the LLM response **before** it is sent to the user.

| Check | Detail |
|---|---|
| PII scrubbing | Redacts emails, phone numbers, Aadhaar numbers |
| Hallucination signals | Detects phrases like `as a language model`, `my training data` and appends a warning |
| Length trim | Truncates responses longer than 1500 characters |
| Empty response | Replaces useless short responses with a fallback message |

### G4 — Observability Logger
Every guardrail event is appended as a structured JSON line to `guardrail_log.jsonl`.

```json
{"timestamp": "2026-03-24T10:30:00", "event": "INPUT_BLOCKED", "query_preview": "ignore previous inst...", "reason": "Prompt injection attempt", "response_preview": ""}
```

Event types: `INPUT_BLOCKED`, `INPUT_FLAGGED`, `OUTPUT_FLAGGED`, `INTERACTION_OK`

## Tech Stack

- **Python 3.8+**
- **Flask**: Full-featured web framework with custom UI
- **Streamlit**: Quick prototype-friendly interface
- **Ollama**: Local LLM inference
  - `nomic-embed-text`: Text embedding model
  - `gemma:latest`: Chat/response generation model
- **Pinecone**: Cloud vector database for semantic search
- **pypdf**: PDF text extraction

## Prerequisites

1. **Python 3.8+** installed on your system
2. **Ollama** installed and running locally
   - Download from: https://ollama.ai/
   - Pull required models:
     ```bash
     ollama pull nomic-embed-text
     ollama pull gemma
     ```
3. **Pinecone Account**
   - Sign up at: https://www.pinecone.io/
   - Create an index with dimension `768` (for nomic-embed-text)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/RAG-Policy-Assistant.git
   cd RAG-Policy-Assistant
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX_NAME=your_index_name
   ```

## Usage

### Option 1: Flask Interface (Recommended for learning)

Run the Flask server:
```bash
python server.py
```

Open http://localhost:5000 in your browser.

**Features:**
- Custom HTML/CSS/JS frontend
- Drag-and-drop PDF upload
- Progress indicator during processing
- Session persistence

### Option 2: Streamlit Interface (Quick & Simple)

Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser.

**Features:**
- Single Python file (~90 lines)
- Built-in chat UI components
- Sidebar for PDF upload
- Chat history management

### Option 3: Command Line (Legacy)

For pre-configured PDF ingestion:
```bash
# First, place your PDF in resources/HRPolicy.pdf
python app.py

# Then query
python UserQuery.py
```

## Flask vs Streamlit: When to Use Which

| Aspect | Flask | Streamlit |
|--------|-------|-----------|
| Code complexity | More (HTML, CSS, JS, Python) | Less (Python only) |
| Customization | Full control | Limited but sufficient |
| Learning value | High (web fundamentals) | Lower |
| Setup speed | Slower | Faster |
| Best for | Production, learning | Prototypes, demos |

## API Endpoints (Flask)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chatbot web interface |
| `/api/upload` | POST | Upload and process a PDF |
| `/api/chat` | POST | Send a query and get a response |
| `/api/status` | GET | Get session status |

### Example: Upload PDF
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "pdf=@/path/to/document.pdf"
```

### Example: Chat Query
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
```

## Project Structure

```
RAG-Policy-Assistant/
├── server.py           # Flask web server with PDF upload
├── streamlit_app.py    # Streamlit alternative interface
├── app.py              # Legacy: Document ingestion for fixed PDF
├── UserQuery.py        # Legacy: Command-line query interface
├── pdfreader.py        # PDF text extraction
├── chunker.py          # Text chunking with overlap
├── embedder.py         # Ollama embedding generation
├── vectorstore.py      # Pinecone operations (returns text + similarity score)
├── llm.py              # LLM response generation with G2 context check
├── guardrails.py       # G1 input · G2 context · G3 output · G4 logging
├── guardrail_log.jsonl # Auto-generated audit log (not tracked)
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not tracked)
├── resources/
│   └── HRPolicy.pdf    # Sample HR policy document
├── templates/
│   └── index.html      # Flask: Chatbot HTML template
└── static/
    ├── css/
    │   └── style.css   # Flask: Chatbot styles
    └── js/
        └── chat.js     # Flask: Chatbot JavaScript
```

## Configuration

### Chunking Parameters
Modify in `chunker.py`:
- `chunk_size`: Characters per chunk (default: 900)
- `chunk_overlap`: Overlap between chunks (default: 150)

### LLM Settings
Modify in `llm.py`:
- `model`: Ollama model name (default: `gemma:latest`)
- `temperature`: Response creativity (default: 0.4)

### Vector Search
Modify in `vectorstore.py`:
- `top_k`: Number of chunks to retrieve (default: 4)

## Troubleshooting

### Ollama Connection Error
Make sure Ollama is running:
```bash
ollama serve
```

### Pinecone Authentication Error
Verify your `.env` file has correct credentials:
```bash
cat .env
```

### Empty Responses
- Ensure a PDF has been uploaded and processed
- Check if Pinecone index has vectors
- Verify Ollama models are downloaded

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
