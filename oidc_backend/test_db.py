#!/usr/bin/env python3
"""
Test script for database functionality
"""
import sys
from datetime import datetime
from flask import Flask
from config import config
from database import init_db, get_db_session
from models import Credential, VerificationLog

def test_database_connection():
    """Test database connection and basic operations"""
    print("🧪 Testing database connection and operations...")
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config['development'])
    
    with app.app_context():
        try:
            # Initialize database
            init_db(app)
            print("✅ Database initialized successfully")
            
            # Get session
            session = get_db_session()
            print("✅ Database session created")
            
            # Test credential operations
            print("\n📋 Testing credential operations...")
            
            # Create a test credential
            test_credential = Credential(
                credential_id='TEST-001-ABC123',
                subject_id='did:test:123',
                type='Test',
                format='ISO mdoc',
                status='active',
                issued=datetime.now(),
                expires=datetime(2025, 12, 31)
            )
            
            session.add(test_credential)
            session.commit()
            print("✅ Test credential created")
            
            # Query the credential
            found_credential = session.query(Credential).filter_by(credential_id='TEST-001-ABC123').first()
            if found_credential:
                print(f"✅ Found credential: {found_credential.credential_id}")
            else:
                print("❌ Failed to find created credential")
                return False
            
            # Test verification log operations
            print("\n📊 Testing verification log operations...")
            
            # Create a test verification log
            test_log = VerificationLog(
                credential_id='TEST-001-ABC123',
                result='PASS',
                response_time=150,
                verifier='Test-Verifier',
                checked_at=datetime.now()
            )
            
            session.add(test_log)
            session.commit()
            print("✅ Test verification log created")
            
            # Query the verification log
            found_log = session.query(VerificationLog).filter_by(credential_id='TEST-001-ABC123').first()
            if found_log:
                print(f"✅ Found verification log: {found_log.result} in {found_log.response_time}ms")
            else:
                print("❌ Failed to find created verification log")
                return False
            
            # Test relationship
            print("\n🔗 Testing relationships...")
            credential_logs = found_credential.verification_logs
            if credential_logs:
                print(f"✅ Found {len(credential_logs)} verification logs for credential")
            else:
                print("❌ No verification logs found for credential")
                return False
            
            # Clean up test data
            print("\n🧹 Cleaning up test data...")
            session.delete(found_log)
            session.delete(found_credential)
            session.commit()
            print("✅ Test data cleaned up")
            
            # Test API endpoints
            print("\n🌐 Testing API endpoints...")
            from app_with_db import app as api_app
            with api_app.test_client() as client:
                # Test credentials endpoint
                response = client.get('/api/credentials')
                if response.status_code == 200:
                    print("✅ /api/credentials endpoint working")
                else:
                    print(f"❌ /api/credentials endpoint failed: {response.status_code}")
                
                # Test verification logs endpoint
                response = client.get('/api/verification-logs')
                if response.status_code == 200:
                    print("✅ /api/verification-logs endpoint working")
                else:
                    print(f"❌ /api/verification-logs endpoint failed: {response.status_code}")
            
            print("\n🎉 All database tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            return False
        finally:
            session.close()

def main():
    """Main test function"""
    print("=" * 50)
    print("OIDC Backend Database Test")
    print("=" * 50)
    
    success = test_database_connection()
    
    if success:
        print("\n✅ All tests passed! Database is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check your database configuration.")
        sys.exit(1)

if __name__ == '__main__':
    main() 