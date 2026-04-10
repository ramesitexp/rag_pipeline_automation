from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from database import engine, SessionLocal
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
    n_results: int = 5

@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    """List all documents and their processing status."""
    documents = db.query(models.Document).all()
    return [{
        "id": d.id, 
        "filename": d.filename, 
        "status": d.status, 
        "created_at": d.created_at
    } for d in documents]

@app.get("/documents/{document_id}")
def get_document_status(document_id: int, db: Session = Depends(get_db)):
    """Get the status of a specific document."""
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
    """Perform RAG: Search context and generate answer."""
    try:
        # 1. Retrieve relevant context
        chunks, metadata = search_documents(request.query, request.n_results)
        
        if not chunks:
            return {"answer": "No relevant documents found.", "context": []}
            
        # 2. Generate answer via OpenAI
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
    """Delete a document from DB, Vector Store, and Disk."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return {"error": "Document not found"}
    
    try:
        # 1. Delete from ChromaDB
        from rag import delete_document_vectors
        delete_document_vectors(doc.filename)
        
        # 2. Delete physical file
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
            
        # 3. Delete from PostgreSQL
        db.delete(doc)
        db.commit()
        
        return {"message": f"Document '{doc.filename}' deleted successfully"}
    except Exception as e:
        return {"error": str(e)}
