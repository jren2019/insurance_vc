#!/usr/bin/env python3
"""
Database management script for OIDC backend
"""
import os
import sys
from datetime import datetime, timedelta
from alembic import command
from alembic.config import Config
from flask import Flask
from config import config
from database import init_db
from models import Credential, VerificationLog

def create_app(config_name='development'):
    """Create Flask app instance"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    return app

def init_database():
    """Initialize database tables"""
    app = create_app()
    with app.app_context():
        init_db(app)
        print("✅ Database initialized successfully!")

def run_migrations():
    """Run database migrations"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("✅ Database migrations completed!")

def seed_database():
    """Seed database with sample data"""
    app = create_app()
    with app.app_context():
        from database import get_db_session
        session = get_db_session()
        
        try:
            # Sample credentials
            sample_credentials = [
                {
                    'credential_id': 'ACC-418277-QLKO',
                    'subject_id': 'did:xyz:fig23',
                    'type': 'Account',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2025, 8, 17),
                    'expires': datetime(2025, 8, 12)
                },
                {
                    'credential_id': 'CUS-919371-AZ5X',
                    'subject_id': None,
                    'type': 'Custom',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2025, 8, 12),
                    'expires': datetime(2025, 10, 11)
                },
                {
                    'credential_id': 'MEM-167754-P2N8',
                    'subject_id': None,
                    'type': 'Membership',
                    'format': 'ISO mdoc',
                    'status': 'revoked',
                    'issued': datetime(2024, 7, 20),
                    'expires': datetime(2025, 3, 21)
                },
                {
                    'credential_id': 'ACC-577898-ZKAC',
                    'subject_id': None,
                    'type': 'Account',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2024, 10, 6),
                    'expires': datetime(2026, 10, 6)
                },
                {
                    'credential_id': 'CUS-240035-I5S8',
                    'subject_id': None,
                    'type': 'Custom',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2024, 9, 12),
                    'expires': datetime(2025, 9, 12)
                },
                {
                    'credential_id': 'MEM-240034-H4R7',
                    'subject_id': None,
                    'type': 'Membership',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2024, 5, 8),
                    'expires': datetime(2025, 11, 8)
                },
                {
                    'credential_id': 'IDT-240031-E104',
                    'subject_id': None,
                    'type': 'Identity',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2024, 5, 8),
                    'expires': datetime(2025, 11, 8)
                },
                {
                    'credential_id': 'ACC-240032-F2P5',
                    'subject_id': None,
                    'type': 'Account',
                    'format': 'ISO mdoc',
                    'status': 'active',
                    'issued': datetime(2024, 5, 8),
                    'expires': datetime(2025, 11, 8)
                }
            ]
            
            # Add credentials
            for cred_data in sample_credentials:
                credential = Credential(**cred_data)
                session.add(credential)
            
            session.commit()
            print(f"✅ Added {len(sample_credentials)} sample credentials")
            
            # Sample verification logs
            sample_logs = [
                {
                    'credential_id': 'EMP-240008-H5R8',
                    'result': 'PASS',
                    'response_time': 167,
                    'verifier': 'Web-Portal-002',
                    'checked_at': datetime(2024, 12, 21, 5, 39)
                },
                {
                    'credential_id': 'ACC-240007-G4Q7',
                    'result': 'PASS',
                    'response_time': 201,
                    'verifier': 'External-API-002',
                    'checked_at': datetime(2024, 12, 21, 4, 28)
                },
                {
                    'credential_id': 'IDT-240006-F3P6',
                    'result': 'PASS',
                    'response_time': 78,
                    'verifier': 'Mobile-App-Android',
                    'checked_at': datetime(2024, 12, 21, 3, 17)
                },
                {
                    'credential_id': 'CUS-240005-E205',
                    'result': 'FAIL',
                    'response_time': 298,
                    'verifier': 'Batch-Processor',
                    'checked_at': datetime(2024, 12, 21, 2, 45)
                },
                {
                    'credential_id': 'MEM-240004-D1N3',
                    'result': 'PASS',
                    'response_time': 145,
                    'verifier': 'Partner-System-A',
                    'checked_at': datetime(2024, 12, 21, 1, 33)
                },
                {
                    'credential_id': 'IDT-240003-C9M1',
                    'result': 'PASS',
                    'response_time': 89,
                    'verifier': 'Mobile-App-iOS',
                    'checked_at': datetime(2024, 12, 20, 23, 22)
                },
                {
                    'credential_id': 'ACC-240002-B8L2',
                    'result': 'PASS',
                    'response_time': 142,
                    'verifier': 'External-API-001',
                    'checked_at': datetime(2024, 12, 20, 22, 15)
                },
                {
                    'credential_id': 'IDT-240001-A7K9',
                    'result': 'PASS',
                    'response_time': 145,
                    'verifier': 'Mobile-App-Android',
                    'checked_at': datetime(2024, 12, 20, 5, 29)
                }
            ]
            
            # Add verification logs
            for log_data in sample_logs:
                log = VerificationLog(**log_data)
                session.add(log)
            
            session.commit()
            print(f"✅ Added {len(sample_logs)} sample verification logs")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error seeding database: {e}")
            raise
        finally:
            session.close()

def show_help():
    """Show help message"""
    print("""
Database Management Script for OIDC Backend

Usage: python manage_db.py <command>

Commands:
    init        - Initialize database tables
    migrate     - Run database migrations
    seed        - Seed database with sample data
    setup       - Initialize, migrate, and seed database
    help        - Show this help message

Examples:
    python manage_db.py init
    python manage_db.py migrate
    python manage_db.py seed
    python manage_db.py setup
    """)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'init':
        init_database()
    elif command == 'migrate':
        run_migrations()
    elif command == 'seed':
        seed_database()
    elif command == 'setup':
        print("🚀 Setting up database...")
        init_database()
        run_migrations()
        seed_database()
        print("✅ Database setup completed!")
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()

if __name__ == '__main__':
    main() 