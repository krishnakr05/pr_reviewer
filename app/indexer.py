# app/indexer.py
import chromadb
from app.embeddings import GeminiEmbeddingFunction

CHROMA_PATH = "./chroma_store"  # persists to disk between requests/restarts

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_or_create_repo_collection(repo_full_name: str):
    """
    One collection per repo, e.g. 'octocat_hello-world'.
    Collection names can't contain slashes, so sanitize.
    """
    client = get_chroma_client()
    collection_name = repo_full_name.replace("/", "_")
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=GeminiEmbeddingFunction(task_type="RETRIEVAL_DOCUMENT"),
        metadata={"hnsw:space": "cosine"},  # cosine similarity fits normalized text embeddings well
    )

def index_repo_files(repo_full_name: str, files: list[dict]):
    """
    files: [{"path": "src/utils/parser.py", "content": "...", "extension": ".py"}, ...]
    Call this once when the GitHub App is installed on a repo, and again
    whenever files change (e.g. on push events) — not on every PR review.
    """
    collection = get_or_create_repo_collection(repo_full_name)

    collection.upsert(
        ids=[f["path"] for f in files],           # file path as stable unique id
        documents=[f["content"] for f in files],   # what actually gets embedded
        metadatas=[{"extension": f["extension"], "path": f["path"]} for f in files],
    )