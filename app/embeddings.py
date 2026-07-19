# app/embeddings.py
from google import genai
from chromadb import Documents, EmbeddingFunction, Embeddings
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

#client = genai.Client()  # picks up GEMINI_API_KEY from env

class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Wraps Gemini's embedding model so Chroma can call it automatically
    on add() and query(). task_type differs depending on whether we're
    storing reference code (RETRIEVAL_DOCUMENT) or embedding a PR diff
    to search with (CODE_RETRIEVAL_QUERY).
    """
    def __init__(self, task_type: str = "RETRIEVAL_DOCUMENT"):
        self.task_type = task_type

    def __call__(self, input: Documents) -> Embeddings:
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
            config={
                "task_type": self.task_type,
                "output_dimensionality": 768,  # smaller = faster/cheaper, minimal quality loss
            },
        )
        return [e.values for e in result.embeddings]