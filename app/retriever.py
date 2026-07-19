# app/retriever.py
from app.indexer import get_chroma_client
from app.embeddings import GeminiEmbeddingFunction

def get_similar_reference_files(
    repo_full_name: str,
    diff_text: str,
    extension: str | None = None,
    top_k: int = 3,
):
    """
    Replaces candidates[:2]. Embeds the current diff and finds the
    top_k most semantically similar reference files already indexed
    for this repo.
    """
    client = get_chroma_client()
    collection_name = repo_full_name.replace("/", "_")

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=GeminiEmbeddingFunction(task_type="RETRIEVAL_DOCUMENT"),
        )
    except Exception:
        return []  # repo not indexed yet — fall back to old behavior upstream

    # Query embedding uses CODE_RETRIEVAL_QUERY — asymmetric from how docs were stored
    query_embedder = GeminiEmbeddingFunction(task_type="CODE_RETRIEVAL_QUERY")
    query_vector = query_embedder([diff_text])[0]

    where_filter = {"extension": extension} if extension else None

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        where=where_filter,   # optional: keep results same-language as the diff
    )

    files = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        files.append({"path": meta["path"], "content": doc, "similarity_distance": dist})
    return files