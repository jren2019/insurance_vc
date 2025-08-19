from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Import models to ensure they are registered
        from models import Credential, VerificationLog
        
        return db

def get_db_session():
    """Get database session"""
    return db.session

def close_db_session():
    """Close database session"""
    db.session.close() 