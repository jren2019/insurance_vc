# file: app.py
from flask import Flask, request, jsonify
import cbor2
import base64
import datetime
from pycose.messages import Sign1Message
from pycose.headers import Algorithm
from pycose.algorithms import Es256
from pycose.keys.keyparam import KpKty
from pycose.keys.keytype import KtyEC2
from pycose.keys.curves import P256
from pycose.keys.ec2 import EC2Key
from pycose.keys.keyparam import EC2KpCurve, EC2KpD, EC2KpX, EC2KpY

app = Flask(__name__)

# -----------------------
# Example issuer private key (for demo only)
# -----------------------
# Replace with a secure key retrieval from AWS KMS / Azure Key Vault / HSM in production.
# The d, x, y values below are raw bytes (example only).
_demo_private_key = EC2Key.from_dict({
    KpKty: KtyEC2,
    EC2KpCurve: P256,
    EC2KpD: bytes.fromhex("1" * 64),  # 32 bytes hex - DO NOT USE IN PROD
    # Optionally include public X/Y if needed:
    # EC2KpX: bytes.fromhex(...),
    # EC2KpY: bytes.fromhex(...),
})

# -----------------------
# Helper: make ISO-like mDoc payload
# -----------------------
def build_mdoc_payload(claims: dict):
    # Minimal example structure — adapt to the ISO namespaces and required fields.
    now = datetime.datetime.utcnow()
    payload = {
        "docType": "org.iso.18013.5.1.mDL",  # ISO document type for mDL (example)
        "iss": "did:example:issuer-12345",   # issuer identifier (could be DID or URL)
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(days=365)).timestamp()),
        "name": claims.get("name"),
        "dateOfBirth": claims.get("dob"),
        # Add whatever ISO claim namespaces/structures you need (address, licence class, etc.)
    }
    return payload

# -----------------------
# Endpoint to issue mDoc
# -----------------------
@app.route("/issue-mdoc", methods=["POST"])
def issue_mdoc():
    """
    Request JSON example:
    {
      "name": "Jane Doe",
      "dob": "1990-01-01",
      "docType": "org.iso.18013.5.1.mDL"
    }
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "missing JSON body"}), 400

    # 1) Build payload
    payload = build_mdoc_payload(data)

    # 2) CBOR encode payload (this is the object that will be signed)
    cbor_payload = cbor2.dumps(payload)

    # 3) Build COSE Sign1 message and sign with ES256
    sign_msg = Sign1Message(
        phdr={Algorithm: Es256},  # protected header: algorithm
        payload=cbor_payload
    )
    sign_msg.key = _demo_private_key
    signed = sign_msg.encode()  # binary COSE_Sign1 message

    # 4) Return as Base64URL for easy transport (compatible with mDOC debuggers)
    b64 = base64.b64encode(signed).decode("ascii")
    b64url = b64.replace('+', '-').replace('/', '_').rstrip('=')
    return jsonify({"mdoc_base64url": b64url})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
