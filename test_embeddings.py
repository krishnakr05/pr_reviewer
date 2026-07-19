from app.embeddings import GeminiEmbeddingFunction

embedder = GeminiEmbeddingFunction(task_type="RETRIEVAL_DOCUMENT")
vectors = embedder(["def add(a, b): return a + b", "class Cat: pass"])

print(f"Number of vectors: {len(vectors)}")
print(f"Length of each vector: {len(vectors[0])}")
print(f"First 5 numbers of vector 1: {vectors[0][:5]}")