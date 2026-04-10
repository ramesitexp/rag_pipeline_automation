from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from database import engine, SessionLocal, get_chroma_collection
import models
from tasks import process_pdf_task
from sqlalchemy.orm import Session
from pydantic import BaseModel
from rag import search_documents, generate_answer

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="RAG Engineering Pipeline API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.on_event("startup")
async def rebuild_vectors_on_startup():
    """
    Render redeploys wipe the container filesystem (ChromaDB + uploads).
    On every startup, if ChromaDB is empty but PostgreSQL has completed
    documents with saved raw_text, re-embed them automatically.
    """
    from embedder import chunk_text, get_embeddings

    collection = get_chroma_collection()
    if collection.count() > 0:
        print("ChromaDB already has data — skipping rebuild.")
        return

    db = SessionLocal()
    try:
        docs = db.query(models.Document).filter(
            models.Document.status == "COMPLETED",
            models.Document.raw_text != None,
            models.Document.raw_text != ""
        ).all()

        if not docs:
            print("No completed documents found in PostgreSQL — nothing to rebuild.")
            return

        print(f"ChromaDB is empty. Rebuilding vectors for {len(docs)} document(s)...")

        for doc in docs:
            try:
                chunks = chunk_text(doc.raw_text)
                if not chunks:
                    continue
                embeddings = get_embeddings(chunks)
                ids = [f"{doc.id}_{i}" for i in range(len(chunks))]
                metadata = [
                    {"document_id": doc.id, "filename": doc.filename, "chunk_index": i}
                    for i in range(len(chunks))
                ]
                collection.add(
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadata,
                    ids=ids
                )
                print(f"Rebuilt: {doc.filename} — {len(chunks)} chunks")
            except Exception as e:
                print(f"Failed to rebuild {doc.filename}: {e}")

        print("Vector rebuild complete.")
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are supported"}

    # 1. Save file to disk
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # 2. Create document record in PostgreSQL
    db_document = models.Document(
        filename=file.filename,
        filepath=file_path,
        status="UPLOADED"
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # 3. Trigger background task to parse, chunk and embed
    background_tasks.add_task(process_pdf_task, db_document.id)

    return {
        "message": "File uploaded successfully. Processing started in background.",
        "document_id": db_document.id,
        "filename": file.filename
    }

class QueryRequest(BaseModel):
    query: str
    n_results: int = 10

@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(models.Document).all()
    return [{
        "id": d.id,
        "filename": d.filename,
        "status": d.status,
        "created_at": d.created_at
    } for d in documents]

@app.get("/documents/{document_id}")
def get_document_status(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return {"error": "Document not found"}
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "created_at": doc.created_at
    }

@app.post("/query")
async def query_rag(request: QueryRequest):
    try:
        chunks, metadata = search_documents(request.query, request.n_results)

        if not chunks:
            return {"answer": "No documents found. Please upload a PDF first.", "sources": []}

        answer = generate_answer(request.query, chunks)

        return {
            "query": request.query,
            "answer": answer,
            "sources": metadata
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return {"error": "Document not found"}

    try:
        from rag import delete_document_vectors
        delete_document_vectors(doc.filename)

        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)

        db.delete(doc)
        db.commit()

        return {"message": f"Document '{doc.filename}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
