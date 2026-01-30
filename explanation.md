# Code Flow Explanation

This document explains how the RAG Policy Assistant works and where each piece of logic is implemented.

## Overview

The application has two main flows:
1. **PDF Ingestion Flow** - Upload and process a PDF document
2. **Query Flow** - Ask questions about the uploaded document

---

## Core Modules

| Module | Purpose |
|--------|---------|
| `pdfreader.py` | Extracts text from PDF files |
| `chunker.py` | Splits text into smaller chunks |
| `embedder.py` | Converts text to vector embeddings using Ollama |
| `vectorstore.py` | Stores/searches vectors in Pinecone |
| `llm.py` | Generates responses using Ollama LLM |

---

## Flow 1: PDF Ingestion (Upload)

**Location:** `server.py` → `/api/upload` endpoint (lines 20-59)

```
User uploads PDF
       ↓
┌─────────────────────────────────────────────────────────────┐
│  server.py - upload_pdf() function                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Receive PDF file from browser                           │
│          ↓                                                  │
│  2. pdfreader.read_pdf_from_file(pdf_file)                 │
│     → Extracts text from each page                          │
│     → Returns: list of page texts                           │
│          ↓                                                  │
│  3. chunker.chunk_pages(pages, chunk_size=900, overlap=150)│
│     → Splits text into overlapping chunks                   │
│     → Returns: list of text chunks                          │
│          ↓                                                  │
│  4. embedder.embed_chunks(chunks)                          │
│     → Sends each chunk to Ollama (nomic-embed-text model)   │
│     → Returns: list of 768-dimensional vectors              │
│          ↓                                                  │
│  5. vectorstore.store_in_pinecone(chunks, embeddings)      │
│     → Stores vectors with metadata in Pinecone              │
│     → Each vector has: id, values, metadata (original text) │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Code Reference:

```python
# server.py - lines 40-44
pages = read_pdf_from_file(pdf_file)
chunks = chunk_pages(pages, chunk_size=900, chunk_overlap=150)
embeddings = embed_chunks(chunks)
store_in_pinecone(chunks, embeddings, namespace=namespace)
```

---

## Flow 2: Query Processing (Chat)

**Location:** `server.py` → `/api/chat` endpoint (lines 61-94)

This is where the **UserQuery.py logic is now implemented**.

```
User asks a question
       ↓
┌─────────────────────────────────────────────────────────────┐
│  server.py - chat() function                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Receive query from browser                              │
│     query = "What is the leave policy?"                     │
│          ↓                                                  │
│  2. embedder.embed_User_query(query)          ← FROM UserQuery.py
│     → Converts query text to vector                         │
│     → Uses same model (nomic-embed-text)                    │
│     → Returns: 768-dimensional vector                       │
│          ↓                                                  │
│  3. vectorstore.search_in_pinecone(query_vector)  ← FROM UserQuery.py
│     → Searches Pinecone for similar vectors                 │
│     → Returns: top 4 matching text chunks                   │
│          ↓                                                  │
│  4. llm.query_llm_with_context(query, matched_chunks) ← FROM UserQuery.py
│     → Sends query + context to Gemma LLM                    │
│     → LLM generates answer based on context                 │
│     → Returns: generated response text                      │
│          ↓                                                  │
│  5. Return response to browser                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Code Reference:

```python
# server.py - lines 77-83
# This is the SAME logic that was in UserQuery.py

query_vector = embed_User_query(user_query)           # Step 1: Embed query
matched_chunks = search_in_pinecone(query_vector, namespace=namespace)  # Step 2: Search
response = query_llm_with_context(user_query, matched_chunks)  # Step 3: Generate
```

### Original UserQuery.py (for comparison):

```python
# UserQuery.py - lines 5-14 (NOW DELETED - logic moved to server.py)

def process_user_query(query: str):
    query_vector = embed_User_query(query)              # Same as server.py line 77
    matched_chunks = search_in_pinecone(query_vector)   # Same as server.py line 80
    generated_response = query_llm_with_context(query, matched_chunks)  # Same as line 83
    print(generated_response)
```

---

## Streamlit Version

**Location:** `streamlit_app.py` (lines 68-85)

The Streamlit version has the same query logic:

```python
# streamlit_app.py - lines 74-82
query_vector = embed_User_query(prompt)
matched_chunks = search_in_pinecone(query_vector, namespace=st.session_state.namespace)
response = query_llm_with_context(prompt, matched_chunks)
```

---

## Module Details

### pdfreader.py

```python
read_pdf(pdf_path)           # Read from file path (legacy)
read_pdf_from_file(file_obj) # Read from uploaded file object (new)
```

### chunker.py

```python
chunk_pages(pages, chunk_size=900, chunk_overlap=150)
# Splits text into chunks with overlap for context preservation
# Example: "Hello world this is a test" with size=10, overlap=3
#   Chunk 1: "Hello worl"
#   Chunk 2: "orl this is"
#   Chunk 3: " is a test"
```

### embedder.py

```python
embed_chunks(chunks)      # Embed multiple chunks (for PDF ingestion)
embed_User_query(query)   # Embed single query (for searching)
# Both use Ollama's nomic-embed-text model
# Returns 768-dimensional vectors
```

### vectorstore.py

```python
store_in_pinecone(chunks, embeddings, namespace)  # Store vectors
search_in_pinecone(query_vector, top_k=4, namespace)  # Find similar vectors
```

### llm.py

```python
query_llm_with_context(query, context, model="gemma:latest")
# System prompt ensures answers are grounded in context
# Temperature=0.4 for consistent, factual responses
```

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FLASK (server.py)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   /api/upload                          /api/chat                        │
│        │                                    │                           │
│        ▼                                    ▼                           │
│   ┌─────────┐                         ┌─────────┐                       │
│   │ PDF     │                         │ Query   │                       │
│   │ Upload  │                         │ Input   │                       │
│   └────┬────┘                         └────┬────┘                       │
│        │                                   │                            │
│        ▼                                   ▼                            │
│   pdfreader.py                        embedder.py                       │
│   (extract text)                      (embed_User_query)                │
│        │                                   │                            │
│        ▼                                   ▼                            │
│   chunker.py                          vectorstore.py                    │
│   (split text)                        (search_in_pinecone)              │
│        │                                   │                            │
│        ▼                                   ▼                            │
│   embedder.py                         llm.py                            │
│   (embed_chunks)                      (query_llm_with_context)          │
│        │                                   │                            │
│        ▼                                   ▼                            │
│   vectorstore.py                      Response                          │
│   (store_in_pinecone)                 to User                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files That Can Be Deleted

| File | Reason |
|------|--------|
| `app.py` | PDF ingestion logic moved to `server.py` `/api/upload` |
| `UserQuery.py` | Query logic moved to `server.py` `/api/chat` |

Both files are now redundant because `server.py` handles everything through the web interface.
