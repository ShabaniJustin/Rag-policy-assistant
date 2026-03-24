import ollama
from guardrails import validate_context

def query_llm_with_context(query: str, matched_chunks: list, model: str = "gemma2:2b"):
    # ── G2: Context confidence check (safety net before LLM call) ────────────
    context_check = validate_context(matched_chunks)
    if not context_check["sufficient"]:
        return context_check["reason"]

    # Extract text from chunks to build context string
    context = "\n\n".join(chunk["text"] for chunk in matched_chunks)

    system_content = """You are a helpful assistant for answering user queries based on provided context.
    use the context to provide accurate and relevant answers. Do not make assumptions beyond the context provided.
    If the context does not contain enough information to answer the query,
    let the user know that you cannot provide an answer based on the given context.
    """
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"}
        ],
        options={"temperature": 0.4}
    )
    return response["message"]["content"]