import ollama

def query_llm_with_context(query: str, context: str, model: str = "gemma:latest"):
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