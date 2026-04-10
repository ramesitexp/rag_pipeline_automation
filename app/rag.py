import os
from openai import OpenAI
from database import get_chroma_collection
from embedder import get_embedding

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def search_documents(query_text: str, n_results: int = 5):
    """
    Search for relevant chunks in ChromaDB.
    """
    collection = get_chroma_collection()
    query_embedding = get_embedding(query_text)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # Extract documents and metadata
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
    context = "\n\n".join(context_chunks)
    
    prompt = f"""
You are an intelligent assistant helping to answer questions based on the provided technical documentation.

### CONTEXT:
{context}

### QUESTION:
{query_text}

### INSTRUCTIONS:
Answer the question accurately using ONLY the context provided. If the answer is not in the context, say "I don't have enough information in the documents to answer that."
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    
    return response.choices[0].message.content
