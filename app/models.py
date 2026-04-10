from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    raw_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="UPLOADED") # UPLOADED, PROCESSING, COMPLETED, FAILED
