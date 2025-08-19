#!/usr/bin/env python3
"""
Test client for OpenID4VCI mdoc issuance
This demonstrates the complete flow to get an mdoc credential
"""

import requests
import json
import jwt
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Configuration
ISSUER_URL = "http://localhost:5000"
ISSUER_AUD = "https://issuer.example.com"  # This should match the ISSUER in app.py
CREDENTIAL_CONFIG_ID = "org.iso.18013.5.1.mDL"

def generate_test_key():
    """Generate a test EC256 key pair for the holder"""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    # Export as JWK
    public_numbers = public_key.public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": base64.urlsafe_b64encode(public_numbers.x.to_bytes(32, 'big')).rstrip(b'=').decode(),
        "y": base64.urlsafe_b64encode(public_numbers.y.to_bytes(32, 'big')).rstrip(b'=').decode(),
        "kid": "test-holder-key"
    }
    
    return private_key, jwk

def get_nonce():
    """Get a nonce from the issuer"""
    response = requests.post(f"{ISSUER_URL}/nonce")
    if response.status_code == 200:
        return response.json()["c_nonce"]
    else:
        raise Exception(f"Failed to get nonce: {response.status_code}")

def create_proof_jwt(private_key, jwk, nonce, aud):
    """Create a JWT proof for proof-of-possession"""
    import time
    
    # Create the JWT payload
    payload = {
        "iss": "test-holder",
        "aud": aud,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,  # 5 minutes
        "nonce": nonce
    }
    
    # Create the JWT header with the holder's public key
    header = {
        "typ": "openid4vci-proof+jwt",
        "alg": "ES256",
        "jwk": jwk
    }
    
    # Sign the JWT
    jwt_token = jwt.encode(payload, private_key, algorithm="ES256", headers=header)
    return jwt_token

def get_credential(proof_jwt, access_token="dummy-token"):
    """Request the credential from the issuer"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    body = {
        "credential_configuration_id": CREDENTIAL_CONFIG_ID,
        "proofs": {
            "jwt": [proof_jwt]
        }
    }
    
    response = requests.post(f"{ISSUER_URL}/credential", headers=headers, json=body)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get credential: {response.status_code} - {response.text}")

def main():
    print("=== OpenID4VCI mdoc Test Client ===")
    
    try:
        # 1. Generate test key pair
        print("1. Generating test key pair...")
        private_key, jwk = generate_test_key()
        print(f"   Generated JWK: {json.dumps(jwk, indent=2)}")
        
        # 2. Get nonce
        print("\n2. Getting nonce...")
        nonce = get_nonce()
        print(f"   Nonce: {nonce}")
        
        # 3. Create proof JWT
        print("\n3. Creating proof JWT...")
        proof_jwt = create_proof_jwt(private_key, jwk, nonce, ISSUER_AUD)
        print(f"   Proof JWT: {proof_jwt}")
        
        # 4. Request credential
        print("\n4. Requesting credential...")
        result = get_credential(proof_jwt)
        print(f"   Credential: {result}")
        
        # 5. Extract the mdoc
        mdoc_b64url = result["credentials"][0]["credential"]
        print(f"\n5. mdoc (base64url): {mdoc_b64url}")
        
        # 6. Test verification
        print("\n6. Testing verification...")
        verify_data = {"cred": mdoc_b64url}
        verify_response = requests.post(f"{ISSUER_URL}/verify", data=verify_data)
        print(f"   Verification response: {verify_response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 