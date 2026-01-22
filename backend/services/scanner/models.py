from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from shared.database import Base


class Scan(Base):
    """User-defined scan configuration"""
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    criteria = Column(Text, nullable=False)  # Criteria expression
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    schedule_cron = Column(String(50))  # Cron expression for scheduled scans
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    results = relationship("ScanResult", back_populates="scan", cascade="all, delete-orphan")


class ScanResult(Base):
    """Scan execution results"""
    __tablename__ = "scan_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)
    executed_at = Column(DateTime, default=datetime.utcnow, index=True)
    matched_symbols = Column(JSON)  # List of symbols that matched
    total_symbols_scanned = Column(Integer)
    execution_time_ms = Column(Integer)  # Execution time in milliseconds
    error = Column(Text)  # Error message if scan failed
    
    # Relationship
    scan = relationship("Scan", back_populates="results")
