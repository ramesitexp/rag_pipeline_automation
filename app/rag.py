import os
from openai import OpenAI
from database import get_chroma_collection
from embedder import get_embedding

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def search_documents(query_text: str, n_results: int = 10):
    """
    Search for relevant chunks in ChromaDB.
    """
    collection = get_chroma_collection()
    query_embedding = get_embedding(query_text)

    # Never request more results than are stored
    available = collection.count()
    if available == 0:
        return [], []
    safe_n = min(n_results, available)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=safe_n
    )

    relevant_chunks = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return relevant_chunks, metadatas

def delete_document_vectors(filename: str):
    """
    Delete all chunks associated with a filename from ChromaDB.
    """
    collection = get_chroma_collection()
    collection.delete(where={"filename": filename})

def generate_answer(query_text: str, context_chunks: list):
    """
    Generate an answer using OpenAI based on the retrieved context.
    """
    context = "\n\n---\n\n".join(context_chunks)

    system_prompt = (
        "You are a helpful assistant that answers questions based on document content. "
        "When asked about stories or documents, summarize and describe what you find. "
        "Be conversational, detailed, and engaging."
    )

    user_prompt = f"""Here is content retrieved from the uploaded document:

{context}

User question: {query_text}

Answer the question using the document content above. If the content contains stories, characters, or events, describe them in detail. Be helpful and thorough."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.5
    )

    return response.choices[0].message.content
