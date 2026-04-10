from sentence_transformers import SentenceTransformer
from typing import List

# Use a lightweight, fast local model for embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Splits text into smaller chunks for vectorization.
    Using simple character-based chunking for demonstration.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        
    return chunks

def get_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for a given text.
    """
    embedding = model.encode(text)
    return embedding.tolist()

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates vector embeddings for a list of texts.
    """
    embeddings = model.encode(texts)
    return [e.tolist() for e in embeddings]
