import os
from typing import List
from openai import OpenAI

# OpenAI embeddings — no local model, no RAM overhead
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBED_MODEL = "text-embedding-3-small"  # 1536-dim, fast, cheap

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - chunk_overlap
    return chunks

def get_embedding(text: str) -> List[float]:
    response = _client.embeddings.create(input=text, model=EMBED_MODEL)
    return response.data[0].embedding

def get_embeddings(texts: List[str]) -> List[List[float]]:
    response = _client.embeddings.create(input=texts, model=EMBED_MODEL)
    return [item.embedding for item in response.data]
