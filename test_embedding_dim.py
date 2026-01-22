import ollama

# Test to find the embedding dimension
test_text = "This is a test"
response = ollama.embeddings(
    model="gemma:latest",
    prompt=test_text
)

embedding = response['embedding']
dimension = len(embedding)

print(f"Embedding dimension for gemma:latest: {dimension}")
print(f"\nPinecone Configuration:")
print(f"  - Dimension: {dimension}")
print(f"  - Metric: cosine (recommended for text embeddings)")
print(f"  - Cloud Provider: aws or gcp (your choice)")
print(f"  - Region: Choose closest to you")
