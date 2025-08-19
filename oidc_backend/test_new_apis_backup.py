#!/usr/bin/env python3
"""
Test script for the new issue_credential and verify_credential APIs
"""
import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:5000"

def test_issue_credential():
    """Test the issue_credential API"""
    print("🧪 Testing issue_credential API...")
    
    # Sample credential data
    credential_data = {
        "credential_id": "TEST-001-ABC123",
        "subject_id": "did:test:123",
        "type": "Identity",
        "format": "ISO mdoc",
        "status": "active",
        "given_name": "John",
        "family_name": "Doe",
        "birth_date": "1990-01-01",
        "custom_fields": {
            "nationality": "US",
            "document_number": "123456789"
        },
        "expires": "2025-12-31T23:59:59"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/issue_credential",
            json=credential_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            result = response.json()
            print("✅ Credential issued successfully!")
            print(f"   Credential ID: {result['credential']['credential_id']}")
            print(f"   Status: {result['credential']['status']}")
            print(f"   Mdoc length: {len(result['mdoc']['base64url'])} characters")
            return result['mdoc']['base64url']
        else:
            print(f"❌ Failed to issue credential: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing issue_credential: {e}")
        return None

def test_verify_credential(credential_b64):
    """Test the verify_credential API"""
    print("\n🧪 Testing verify_credential API...")
    
    if not credential_b64:
        print("❌ No credential to verify")
        return
    
    verification_data = {
        "credential": credential_b64,
        "verifier": "Test-API-Verifier"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/verify_credential",
            json=verification_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Credential verified successfully!")
            print(f"   Result: {result['verification']['result']}")
            print(f"   Response Time: {result['verification']['response_time_ms']}ms")
            print(f"   Signature Valid: {result['verification']['signature_valid']}")
            print(f"   Digests Valid: {result['verification']['digests_valid']}")
        else:
            print(f"❌ Failed to verify credential: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing verify_credential: {e}")

def test_get_credentials():
    """Test getting credentials from database"""
    print("\n🧪 Testing get credentials API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/credentials")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} credentials in database")
            for cred in result['data'][:3]:  # Show first 3
                print(f"   - {cred['credential_id']} ({cred['type']}) - {cred['status']}")
        else:
            print(f"❌ Failed to get credentials: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing get credentials: {e}")

def test_get_verification_logs():
    """Test getting verification logs from database"""
    print("\n🧪 Testing get verification logs API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/verification-logs")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} verification logs in database")
            for log in result['data'][:3]:  # Show first 3
                print(f"   - {log['credential_id']} - {log['result']} ({log['response_time']}ms)")
        else:
            print(f"❌ Failed to get verification logs: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing get verification logs: {e}")

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing New OIDC APIs")
    print("=" * 60)
    
    # Test credential issuance
    credential_b64 = test_issue_credential()
    
    # Test credential verification
    test_verify_credential(credential_b64)
    
    # Test database queries
    test_get_credentials()
    test_get_verification_logs()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main() 