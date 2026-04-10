import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import chromadb

# PostgreSQL Connection Pipeline
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/rag_db")
# Render provides "postgres://" but SQLAlchemy requires "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ChromaDB Connection Pipeline
# If CHROMA_DB_URL is set, connect via HTTP (Docker / paid Render service).
# Otherwise use embedded persistent client (free Render tier — data is ephemeral).
CHROMA_DB_URL = os.getenv("CHROMA_DB_URL", "")

if CHROMA_DB_URL:
    if not CHROMA_DB_URL.startswith("http"):
        CHROMA_DB_URL = "http://" + CHROMA_DB_URL
    _parsed = urlparse(CHROMA_DB_URL)
    chroma_host = _parsed.hostname or "localhost"
    chroma_port = _parsed.port or 8000
    try:
        chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    except Exception as e:
        print(f"Failed to connect to Chroma HTTP Client: {e}. Falling back to embedded client.")
        chroma_client = chromadb.EphemeralClient()
else:
    # Embedded mode: stores data at CHROMA_PERSIST_DIR (defaults to /app/chroma_data)
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/app/chroma_data")
    os.makedirs(persist_dir, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=persist_dir)

# Get or create collection
collection = chroma_client.get_or_create_collection(name="pdf_documents")

def get_chroma_collection():
    return collection
