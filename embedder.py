import ollama
from typing import List

# Ollama embedding model
EMBEDDING_MODEL = "nomic-embed-text:latest"


def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """Embeds chunks using Ollama's embedding model."""
    embeddings = []
    for chunk in chunks:
        response = ollama.embeddings(
            model=EMBEDDING_MODEL,
            prompt=chunk
        )
        embeddings.append(response['embedding'])

    return embeddings


def embed_User_query(query: str) -> List[float]:
    """Embeds a user query using Ollama's embedding model."""
    response = ollama.embeddings(
        model=EMBEDDING_MODEL,
        prompt=query
    )
    return response['embedding']