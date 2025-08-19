#!/usr/bin/env python3
"""
Test Data Population Script for OIDC Backend
This script populates the database with sample credentials and verification logs for testing.
"""
import sys
import random
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy import func
from config import config
from database import init_db, get_db_session
from models import Credential, VerificationLog

def create_app(config_name='development'):
    """Create Flask app instance"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    return app

def generate_credential_id(prefix, index):
    """Generate a realistic credential ID"""
    import hashlib
    base = f"{prefix}-{index:06d}"
    hash_part = hashlib.md5(base.encode()).hexdigest()[:4].upper()
    return f"{prefix}-{index:06d}-{hash_part}"

def populate_test_data():
    """Populate database with comprehensive test data"""
    print("🚀 Populating database with test data...")
    
    app = create_app()
    with app.app_context():
        init_db(app)
        session = get_db_session()
        
        try:
            # Clear existing data (optional - comment out if you want to keep existing data)
            print("🧹 Clearing existing data...")
            session.query(VerificationLog).delete()
            session.query(Credential).delete()
            session.commit()
            print("✅ Existing data cleared")
            
            # Sample credential types and their prefixes
            credential_types = [
                ("Account", "ACC"),
                ("Identity", "IDT"),
                ("Membership", "MEM"),
                ("Custom", "CUS"),
                ("Employee", "EMP"),
                ("Student", "STU"),
                ("Driver", "DRV"),
                ("Medical", "MED")
            ]
            
            # Sample names for realistic data
            first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", 
                          "James", "Maria", "William", "Anna", "Richard", "Sofia", "Joseph", "Emma",
                          "Thomas", "Olivia", "Christopher", "Ava", "Daniel", "Isabella", "Matthew", "Mia"]
            
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                         "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                         "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson"]
            
            # Sample verifiers
            verifiers = [
                "Web-Portal-001", "Web-Portal-002", "Mobile-App-Android", "Mobile-App-iOS",
                "External-API-001", "External-API-002", "Batch-Processor", "Partner-System-A",
                "Partner-System-B", "Internal-Verifier", "Test-System", "Demo-Verifier"
            ]
            
            # Generate credentials
            print("📋 Generating credentials...")
            credentials = []
            
            for i, (cred_type, prefix) in enumerate(credential_types, 1):
                for j in range(1, 6):  # 5 credentials per type
                    credential_id = generate_credential_id(prefix, i * 100 + j)
                    
                    # Random subject ID (some with DID format, some without)
                    if random.choice([True, False]):
                        subject_id = f"did:org.issuance-vc.bank.account:holder-{random.randint(1000, 9999)}"
                    else:
                        subject_id = None
                    
                    # Random status (mostly active, some revoked)
                    status = "active" if random.random() > 0.1 else "revoked"
                    
                    # Random dates
                    issued_date = datetime.now() - timedelta(days=random.randint(1, 365))
                    expires_date = issued_date + timedelta(days=random.randint(30, 730))
                    
                    # Some credentials don't expire
                    if random.random() > 0.8:
                        expires_date = None
                    
                    credential = Credential(
                        credential_id=credential_id,
                        subject_id=subject_id,
                        type=cred_type,
                        format="ISO mdoc",
                        status=status,
                        issued=issued_date,
                        expires=expires_date
                    )
                    
                    credentials.append(credential)
                    session.add(credential)
            
            # Create placeholder credentials for unknown ones
            print("🔍 Creating placeholder credentials for unknown verification logs...")
            unknown_credentials = [
                "UNKNOWN-001-ABCD", "UNKNOWN-002-EFGH", "UNKNOWN-003-IJKL",
                "EXTRACTED-mDL", "EXTRACTED-credential", "EXTRACTED-document"
            ]
            
            for unknown_cred in unknown_credentials:
                # Create a placeholder credential for each unknown credential ID
                placeholder_credential = Credential(
                    credential_id=unknown_cred,
                    subject_id=None,
                    type="Unknown",
                    format="ISO mdoc",
                    status="active",
                    issued=datetime.now() - timedelta(days=random.randint(1, 30)),
                    expires=None
                )
                credentials.append(placeholder_credential)
                session.add(placeholder_credential)
            
            session.commit()
            print(f"✅ Created {len(credentials)} credentials (including placeholders)")
            
            # Generate verification logs
            print("📊 Generating verification logs...")
            verification_logs = []
            
            for credential in credentials:
                # Each credential gets 1-5 verification attempts
                num_verifications = random.randint(1, 5)
                
                for k in range(num_verifications):
                    # Random verification date (within last 30 days)
                    checked_at = datetime.now() - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    
                    # Random result (mostly PASS, some FAIL)
                    result = "PASS" if random.random() > 0.15 else "FAIL"
                    
                    # Random response time (50-500ms)
                    response_time = random.randint(50, 500)
                    
                    # Random verifier
                    verifier = random.choice(verifiers)
                    
                    verification_log = VerificationLog(
                        credential_id=credential.credential_id,
                        result=result,
                        response_time=response_time,
                        verifier=verifier,
                        checked_at=checked_at
                    )
                    
                    verification_logs.append(verification_log)
                    session.add(verification_log)
            
            session.commit()
            print(f"✅ Created {len(verification_logs)} verification logs")
            
            # Print summary statistics
            print("\n📈 Database Population Summary:")
            print("=" * 50)
            
            total_credentials = session.query(Credential).count()
            total_verifications = session.query(VerificationLog).count()
            
            print(f"Total Credentials: {total_credentials}")
            print(f"Total Verification Logs: {total_verifications}")
            
            # Credential type breakdown
            print("\nCredential Types:")
            cred_types = session.query(Credential.type).distinct().all()
            for (cred_type,) in cred_types:
                count = session.query(Credential).filter_by(type=cred_type).count()
                print(f"  {cred_type}: {count}")
            
            # Status breakdown
            print("\nCredential Status:")
            active_count = session.query(Credential).filter_by(status='active').count()
            revoked_count = session.query(Credential).filter_by(status='revoked').count()
            print(f"  Active: {active_count}")
            print(f"  Revoked: {revoked_count}")
            
            # Verification result breakdown
            print("\nVerification Results:")
            pass_count = session.query(VerificationLog).filter_by(result='PASS').count()
            fail_count = session.query(VerificationLog).filter_by(result='FAIL').count()
            print(f"  PASS: {pass_count}")
            print(f"  FAIL: {fail_count}")
            
            # Average response time
            avg_response_time = session.query(func.avg(VerificationLog.response_time)).scalar()
            print(f"\nAverage Response Time: {avg_response_time:.1f}ms")
            
            print("\n🎉 Test data population completed successfully!")
            print("\nYou can now:")
            print("1. Start the application: python app_with_db.py")
            print("2. View the dashboard: http://localhost:5000/dashboard")
            print("3. Test the APIs: python test_new_apis.py")
            
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error populating test data: {e}")
            return False
        finally:
            session.close()

def main():
    """Main function"""
    print("=" * 60)
    print("OIDC Backend Test Data Population")
    print("=" * 60)
    
    success = populate_test_data()
    
    if success:
        print("\n✅ Test data population completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test data population failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
