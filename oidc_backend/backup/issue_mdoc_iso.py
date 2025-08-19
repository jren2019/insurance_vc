# file: issue_mdoc_iso.py
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

# -------------------------
# DEMO KEY (for local testing ONLY)
# -------------------------
# 32-byte private scalar hex (demo). Never use in production.
_demo_d_hex = "0f" * 32  # replace with secure storage in production
_demo_key = EC2Key.from_dict({
    KpKty: KtyEC2,
    EC2KpCurve: P256,
    EC2KpD: bytes.fromhex(_demo_d_hex),
    # For pycose some versions also expect X/Y; pycose can derive from D in many cases.
})

# -------------------------
# ISO/AAMVA Namespaces
# -------------------------
ISO_NS = "org.iso.18013.5.1"
AAMVA_NS = "org.iso.18013.5.1.aamva"  # AAMVA-specific extension namespace per guidance


def build_iso_mdoc_payload(claims: dict):
    """
    Build ISO 18013-5 style payload map keyed by namespaces.
    """
    now = datetime.datetime.utcnow()

    mdl_ns = {
        "given_name": claims.get("givenName"),
        "family_name": claims.get("familyName"),
        "date_of_birth": claims.get("dateOfBirth"),
        "document_number": claims.get("documentNumber"),
    }

    aamva_ns = {}
    if claims.get("issuing_jurisdiction"):
        aamva_ns["issuing_jurisdiction"] = claims.get("issuing_jurisdiction")
    if claims.get("domestic_driving_privileges"):
        aamva_ns["domestic_driving_privileges"] = claims.get("domestic_driving_privileges")

    payload = {
        "docType": claims.get("docType", "org.iso.18013.5.1.mDL"),
        "iss": claims.get("issuer", "did:example:issuer-12345"),
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(days=365)).timestamp()),
        ISO_NS + ".mdl": mdl_ns,
    }

    if aamva_ns:
        payload[AAMVA_NS] = aamva_ns

    return payload


@app.route("/issue-mdoc-iso", methods=["POST"])
def issue_mdoc_iso():
    """
    Accepts JSON body with claim fields and returns Base64URL-encoded COSE_Sign1 mDoc.
    Example POST body:
    {
      "givenName": "Jane",
      "familyName": "Doe",
      "dateOfBirth": "1990-01-01",
      "documentNumber": "D1234567",
      "issuing_jurisdiction": "US-CA",
      "domestic_driving_privileges": {"class": "C", "from": "2020-01-01"},
      "issuer": "did:example:issuer-12345",
      "docType": "org.iso.18013.5.1.mDL"
    }
    """
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "missing json body"}), 400

    # 1) Build ISO-structured payload (CBOR map keyed by namespace URI strings)
    payload_obj = build_iso_mdoc_payload(data)

    # 2) CBOR encode
    cbor_payload = cbor2.dumps(payload_obj)

    # 3) Create COSE_Sign1 and sign (ES256)
    msg = Sign1Message(phdr={Algorithm: Es256}, payload=cbor_payload)
    msg.key = _demo_key
    signed = msg.encode()  # binary COSE_Sign1

    # 4) Return Base64URL for transport (compatible with mDOC debuggers)
    b64 = base64.b64encode(signed).decode("ascii")
    b64url = b64.replace('+', '-').replace('/', '_').rstrip('=')
    return jsonify({"mdoc_base64url": b64url})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
