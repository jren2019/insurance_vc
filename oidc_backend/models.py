from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Credential(Base):
    """Credential model representing the credential table"""
    __tablename__ = 'credential'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    credential_id = Column(String(50), unique=True, nullable=False, index=True)
    subject_id = Column(String(255), nullable=True)  # can be null as shown in image
    type = Column(String(50), nullable=False)  # Account, Custom, Membership, Identity
    format = Column(String(50), nullable=False, default='ISO mdoc')
    status = Column(String(20), nullable=False, default='active')  # active, revoked
    issued = Column(DateTime, nullable=False, default=func.now())
    expires = Column(DateTime, nullable=True)  # can be null for "Never" expiry
    
    # Relationship to verification logs
    verification_logs = relationship("VerificationLog", back_populates="credential")
    
    def __repr__(self):
        return f"<Credential(id={self.id}, credential_id='{self.credential_id}', type='{self.type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'credential_id': self.credential_id,
            'subject_id': self.subject_id,
            'type': self.type,
            'format': self.format,
            'status': self.status,
            'issued': self.issued.isoformat() if self.issued else None,
            'expires': self.expires.isoformat() if self.expires else None
        }

class VerificationLog(Base):
    """Verification log model representing the verification_log table"""
    __tablename__ = 'verification_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    checked_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    credential_id = Column(String(50), ForeignKey('credential.credential_id'), nullable=False, index=True)
    result = Column(String(10), nullable=False)  # PASS, FAIL
    response_time = Column(Integer, nullable=False)  # milliseconds
    verifier = Column(String(100), nullable=False)  # Web-Portal-002, External-API-002, etc.
    
    # Relationship to credential
    credential = relationship("Credential", back_populates="verification_logs")
    
    def __repr__(self):
        return f"<VerificationLog(id={self.id}, credential_id='{self.credential_id}', result='{self.result}', verifier='{self.verifier}')>"
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
            'credential_id': self.credential_id,
            'result': self.result,
            'response_time': self.response_time,
            'verifier': self.verifier
        } 