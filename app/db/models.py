from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.db.database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String, nullable=False)
    repo = Column(String, nullable=False)
    pull_number = Column(Integer, nullable=False)
    head_sha = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending | completed | failed
    total_findings = Column(Integer, default=0)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, nullable=False)
    filename = Column(String, nullable=False)
    line = Column(Integer, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())