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
CHROMA_DB_URL = os.getenv("CHROMA_DB_URL", "http://vectordb:8000")
# Support both "http://host:port" and bare "host:port" formats (Render uses hostport)
if not CHROMA_DB_URL.startswith("http"):
    CHROMA_DB_URL = "http://" + CHROMA_DB_URL
_parsed = urlparse(CHROMA_DB_URL)
chroma_host = _parsed.hostname or "vectordb"
chroma_port = _parsed.port or 8000

try:
    chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
except Exception as e:
    # Fallback to ephemeral client for testing outside docker
    print(f"Failed to connect to Chroma HTTP Client. Error: {e}")
    chroma_client = chromadb.Client()

# Get or create collection
collection = chroma_client.get_or_create_collection(name="pdf_documents")

def get_chroma_collection():
    return collection
