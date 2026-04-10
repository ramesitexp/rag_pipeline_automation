from sqlalchemy.orm import Session
from database import SessionLocal, get_chroma_collection
from models import Document
from parser import parse_pdf
from embedder import chunk_text, get_embeddings
import uuid

def process_pdf_task(document_id: int):
    """
    Background task to parse PDF, store text in warehouse, and vectorize into ChromaDB.
    """
    db = SessionLocal()
    
    try:
        # Fetch the document from DB
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            print(f"Document {document_id} not found.")
            return

        # 1. Update status
        doc.status = "PROCESSING"
        db.commit()

        # 2. Parse PDF
        print(f"Parsing PDF: {doc.filename}")
        raw_text = parse_pdf(doc.filepath)
        doc.raw_text = raw_text
        db.commit()

        # 3. Chunk text
        print(f"Chunking text for {doc.filename}")
        chunks = chunk_text(raw_text)

        if chunks:
            # 4. Generate Embeddings
            print(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = get_embeddings(chunks)
            
            # 5. Store in ChromaDB
            print("Storing in ChromaDB...")
            collection = get_chroma_collection()
            
            # Generate unique IDs for each chunk
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]
            metadata = [{"document_id": document_id, "filename": doc.filename, "chunk_index": i} for i in range(len(chunks))]
            
            collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadata,
                ids=ids
            )
            
        doc.status = "COMPLETED"
        db.commit()
        print(f"Successfully processed {doc.filename}")

    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "FAILED"
            db.commit()
    finally:
        db.close()
