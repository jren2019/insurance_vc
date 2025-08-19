from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import base64, cbor2, datetime, hashlib, os, secrets, time, json
from cbor2 import CBORTag
import re

import jwt  # PyJWT
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from cryptography import x509
from cryptography.x509 import NameOID
from cryptography.hazmat.primitives import hashes
import tempfile

# COSE (for verification UI)
from pycose.messages import Sign1Message
from pycose.keys.ec2 import EC2Key
from pycose.keys.curves import P256

# pymdoccbor helper
from pymdoccbor.mdoc.issuer import MdocCborIssuer

# Database imports
from config import config
from database import init_db, get_db_session
from models import Credential, VerificationLog

app = Flask(__name__)

# Initialize CORS
CORS(app, origins=["http://localhost:4200", re.compile(r"https://.*\.ngrok-free\.app")], supports_credentials=True)

# Load configuration
app.config.from_object(config['development'])

# Initialize database
init_db(app)

# ---------------------------------------------------------------------
# Config (demo)
# ---------------------------------------------------------------------
ISSUER = app.config.get('ISSUER', "https://issuer.example.com")
CONFIG_ID = app.config.get('CONFIG_ID', "org.iso.18013.5.1.mDL")
ALG_COSE = app.config.get('ALG_COSE', -7)
ALG_JOSE = app.config.get('ALG_JOSE', "ES256")

# In-memory stores (use Redis/DB in production)
PRE_AUTH_CODES = {}    # code -> {"config_id": str, "created": int}
ACCESS_TOKENS = {}     # token -> {"expires": int}
NONCES = {}            # c_nonce -> expires_at

# ---------------------------------------------------------------------
# Demo issuer key (static; replace with KMS/HSM in prod)
# ---------------------------------------------------------------------
ISSUER_D_HEX = "11" * 32  # 32-byte hex scalar (demo only!)
_issuer_d_int = int(ISSUER_D_HEX, 16)
_crypto_priv = ec.derive_private_key(_issuer_d_int, ec.SECP256R1())
_crypto_pub = _crypto_priv.public_key()
_pub_nums = _crypto_pub.public_numbers()
_ISSUER_X = _pub_nums.x.to_bytes(32, "big")
_ISSUER_Y = _pub_nums.y.to_bytes(32, "big")
_ISSUER_D = _issuer_d_int.to_bytes(32, "big")

# COSE keys for verification UI
_ISSUER_SIGN_KEY = EC2Key(crv=P256, x=_ISSUER_X, y=_ISSUER_Y, d=_ISSUER_D)
_ISSUER_VERIFY_KEY = EC2Key(crv=P256, x=_ISSUER_X, y=_ISSUER_Y)  # public only

# pymdoccbor expects COSE-like dict for the private key
ISSUER_PKEY = {
    "KTY": "EC2",
    "CURVE": "P_256",
    "ALG": "ES256",
    "D": _ISSUER_D,            # private scalar bytes
    "KID": b"issuer-demo-kid"  # optional
}

# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def b64url_decode_to_bytes(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)

def jwk_to_cose_ec2_map(jwk: dict) -> dict:
    """COSE_Key (CBOR map) using integer labels, as required by ISO mdoc."""
    def b64u_decode(b64s: str) -> bytes:
        pad = "=" * ((4 - len(b64s) % 4) % 4)
        return base64.urlsafe_b64decode(b64s + pad)
    assert jwk.get("kty") == "EC" and jwk.get("crv") in ("P-256", "secp256r1")
    x = b64u_decode(jwk["x"])
    y = b64u_decode(jwk["y"])
    cose_key = {
        1: 2,     # kty: EC2
        -1: 1,    # crv: P-256
        -2: x,    # x
        -3: y,    # y
    }
    if jwk.get("kid"):
        cose_key[2] = jwk["kid"].encode()
    return cose_key

def verify_jwt_proof(proof_jwt: str, aud: str):
    """Validate 'openid4vci-proof+jwt' with embedded holder JWK, aud, and nonce."""
    header = jwt.get_unverified_header(proof_jwt)
    if header.get("typ") != "openid4vci-proof+jwt":
        raise ValueError("invalid proof typ")
    holder_jwk = header.get("jwk")
    if not holder_jwk:
        raise ValueError("missing holder jwk")

    def b64u_decode(s: str) -> bytes:
        pad = "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s + pad)
    x_int = int.from_bytes(b64u_decode(holder_jwk["x"]), "big")
    y_int = int.from_bytes(b64u_decode(holder_jwk["y"]), "big")
    pub_numbers = ec.EllipticCurvePublicNumbers(x_int, y_int, ec.SECP256R1())
    pub_key = pub_numbers.public_key()

    pem = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    claims = jwt.decode(proof_jwt, key=pem, algorithms=[ALG_JOSE], audience=aud)
    now = int(time.time())
    nonce = claims.get("nonce")
    if not nonce or nonce not in NONCES or NONCES[nonce] < now:
        raise ValueError("nonce invalid/expired")
    del NONCES[nonce]  # one-time use
    return holder_jwk, claims

def _selfsigned_cert_der_ec(priv_key, cn="Demo DS (not for prod)", days=365) -> bytes:
    now = datetime.datetime.utcnow()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(priv_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    )
    cert = builder.sign(private_key=priv_key, algorithm=hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.DER)

def _write_temp_der(der_bytes: bytes) -> str:
    fd, path = tempfile.mkstemp(prefix="issuer_ds_", suffix=".der")
    with os.fdopen(fd, "wb") as f:
        f.write(der_bytes)
    return path

# ---------- Robust CBOR helpers --------------------------------------
def _untag_deep(obj):
    """Recursively strip CBOR tags anywhere in the structure."""
    if isinstance(obj, CBORTag):
        return _untag_deep(obj.value)
    if isinstance(obj, dict):
        return { _untag_deep(k): _untag_deep(v) for k, v in obj.items() }
    if isinstance(obj, list):
        return [ _untag_deep(x) for x in obj ]
    return obj

def _as_bytes(x: object) -> bytes:
    """Return raw bytes from possibly-tagged bytes/bytearray."""
    x = _untag_deep(x)
    if isinstance(x, bytes):
        return x
    if isinstance(x, bytearray):
        return bytes(x)
    raise TypeError(f"Expected bytes, got {type(x)}")

def _to_str_key(k):
    k = _untag_deep(k)
    if isinstance(k, (bytes, bytearray)):
        return k.decode()
    return k

def _norm_ns_keys(d):
    """Normalize namespace map keys to str (deep-untag first)."""
    d = _untag_deep(d)
    return { _to_str_key(k): v for k, v in d.items() }

def _extract_issuersigned(decoded_any):
    """
    Accepts any mdoc/IssuerSigned encoding variant and returns a dict
    that has at least keys: 'issuerAuth' and 'nameSpaces'.
    """
    d = _untag_deep(decoded_any)

    # Direct IssuerSigned dict
    if isinstance(d, dict) and "issuerAuth" in d and "nameSpaces" in d:
        return _untag_deep(d)

    # Array form: [IssuerSigned, DeviceSigned?]
    if isinstance(d, list) and d:
        first = _untag_deep(d[0])
        if isinstance(first, dict) and "issuerAuth" in first and "nameSpaces" in first:
            return _untag_deep(first)

    # Wrapper form: { status, version, documents: [ { issuerSigned: ... } ] }
    if isinstance(d, dict) and "documents" in d:
        docs = d.get("documents") or []
        if isinstance(docs, list) and docs:
            doc0 = _untag_deep(docs[0])
            if isinstance(doc0, dict) and "issuerSigned" in doc0:
                isd = _untag_deep(doc0["issuerSigned"])
                if isinstance(isd, list) and isd:
                    isd = _untag_deep(isd[0])
                if isinstance(isd, dict) and "issuerAuth" in isd and "nameSpaces" in isd:
                    return _untag_deep(isd)

    raise ValueError("Could not locate IssuerSigned in decoded structure")

def _sign1_from_issuer_auth(issuer_auth):
    """
    Accept issuerAuth as:
      - bytes: encoded COSE_Sign1 (tagged or untagged)
      - list:  [protected bstr, unprotected dict, payload bstr, signature bstr]
      - CBORTag: a tagged COSE structure
    Return a pycose Sign1Message, ensuring tag(18) when necessary.
    """
    # Handle CBORTag first - extract the value
    if isinstance(issuer_auth, CBORTag):
        issuer_auth = issuer_auth.value
    
    # bytes / bytearray path
    if isinstance(issuer_auth, (bytes, bytearray)):
        try:
            return Sign1Message.decode(issuer_auth)
        except Exception:
            # Decode to obj, deep-untag, then re-encode with proper tag if needed
            loaded = _untag_deep(cbor2.loads(issuer_auth))
            if isinstance(loaded, list) and len(loaded) == 4:
                return Sign1Message.decode(cbor2.dumps(CBORTag(18, loaded)))
            # If it's already a tagged Sign1 or equivalent structure, re-dump
            return Sign1Message.decode(cbor2.dumps(loaded))

    # raw COSE array
    if isinstance(issuer_auth, list) and len(issuer_auth) == 4:
        return Sign1Message.decode(cbor2.dumps(CBORTag(18, issuer_auth)))

    raise ValueError(f"Unsupported issuerAuth type: {type(issuer_auth)}")

# ---------------------------------------------------------------------
# Database API Endpoints
# ---------------------------------------------------------------------

@app.route('/api/credentials', methods=['GET'])
def get_credentials():
    """Get all credentials"""
    try:
        session = get_db_session()
        credentials = session.query(Credential).all()
        return jsonify({
            'success': True,
            'data': [cred.to_dict() for cred in credentials],
            'count': len(credentials)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/credentials/<credential_id>', methods=['GET'])
def get_credential(credential_id):
    """Get a specific credential by ID"""
    try:
        session = get_db_session()
        credential = session.query(Credential).filter_by(credential_id=credential_id).first()
        if credential:
            return jsonify({'success': True, 'data': credential.to_dict()})
        else:
            return jsonify({'success': False, 'error': 'Credential not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/credentials', methods=['POST'])
def create_credential():
    """Create a new credential"""
    try:
        data = request.get_json()
        session = get_db_session()
        
        # Check if credential_id already exists
        existing = session.query(Credential).filter_by(credential_id=data['credential_id']).first()
        if existing:
            return jsonify({'success': False, 'error': 'Credential ID already exists'}), 400
        
        credential = Credential(**data)
        session.add(credential)
        session.commit()
        
        return jsonify({'success': True, 'data': credential.to_dict()}), 201
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verification-logs', methods=['GET'])
def get_verification_logs():
    """Get all verification logs"""
    try:
        session = get_db_session()
        logs = session.query(VerificationLog).order_by(VerificationLog.checked_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs],
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verification-logs', methods=['POST'])
def create_verification_log():
    """Create a new verification log entry"""
    try:
        data = request.get_json()
        session = get_db_session()
        
        # Verify that the credential exists
        credential = session.query(Credential).filter_by(credential_id=data['credential_id']).first()
        if not credential:
            return jsonify({'success': False, 'error': 'Credential not found'}), 404
        
        log = VerificationLog(**data)
        session.add(log)
        session.commit()
        
        return jsonify({'success': True, 'data': log.to_dict()}), 201
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/credentials/<credential_id>/verification-logs', methods=['GET'])
def get_credential_verification_logs(credential_id):
    """Get verification logs for a specific credential"""
    try:
        session = get_db_session()
        logs = session.query(VerificationLog).filter_by(credential_id=credential_id).order_by(VerificationLog.checked_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs],
            'count': len(logs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------------------------------------------------------------------
# Well-known (metadata)
# ---------------------------------------------------------------------
@app.get("/.well-known/oauth-authorization-server")
def oauth_as_meta():
    return jsonify({
        "issuer": ISSUER,
        "token_endpoint": f"{ISSUER}/token",
        "grant_types_supported": ["urn:ietf:params:oauth:grant-type:pre-authorized_code"]
    })

@app.get("/.well-known/openid-credential-issuer")
def openid4vci_meta():
    return jsonify({
        "credential_issuer": ISSUER,
        "credential_endpoint": f"{ISSUER}/credential",
        "nonce_endpoint": f"{ISSUER}/nonce",
        "credential_configurations_supported": {
            CONFIG_ID: {
                "format": "mso_mdoc",
                "doctype": "org.iso.18013.5.1.mDL",
                "cryptographic_binding_methods_supported": ["cose_key"],
                "credential_signing_alg_values_supported": [ALG_COSE],  # COSE alg ids
                "proof_types_supported": {
                    "jwt": {"proof_signing_alg_values_supported": [ALG_JOSE]}  # JOSE alg names
                },
                "credential_metadata": {
                    "display": [{"name": "Mobile Driving Licence", "locale": "en-US"}],
                    "claims": [
                        {"path": ["org.iso.18013.5.1", "given_name"]},
                        {"path": ["org.iso.18013.5.1", "family_name"]},
                        {"path": ["org.iso.18013.5.1", "birth_date"], "mandatory": True}
                    ]
                }
            }
        }
    })

# ---------------------------------------------------------------------
# Offer (pre-authorized)
# ---------------------------------------------------------------------
@app.post("/offer")
def offer():
    code = secrets.token_urlsafe(24)
    PRE_AUTH_CODES[code] = {"config_id": CONFIG_ID, "created": int(time.time())}
    offer_obj = {
        "credential_issuer": ISSUER,
        "credential_configuration_ids": [CONFIG_ID],
        "grants": {
            "urn:ietf:params:oauth:grant-type:pre-authorized_code": {
                "pre-authorized_code": code
            }
        }
    }
    return jsonify({"credential_offer": offer_obj})

# ---------------------------------------------------------------------
# Token (pre-authorized_code)
# ---------------------------------------------------------------------
@app.post("/token")
def token():
    gt = request.form.get("grant_type")
    if gt != "urn:ietf:params:oauth:grant-type:pre-authorized_code":
        return jsonify({"error": "unsupported_grant_type"}), 400
    code = request.form.get("pre-authorized_code")
    if not code or code not in PRE_AUTH_CODES:
        return jsonify({"error": "invalid_grant"}), 400
    del PRE_AUTH_CODES[code]  # single-use

    access_token = secrets.token_urlsafe(32)
    ACCESS_TOKENS[access_token] = {"expires": int(time.time()) + 600}
    return jsonify({"access_token": access_token, "token_type": "Bearer", "expires_in": 600})

# ---------------------------------------------------------------------
# Nonce endpoint
# ---------------------------------------------------------------------
@app.post("/nonce")
def nonce():
    c_nonce = secrets.token_urlsafe(24)
    NONCES[c_nonce] = int(time.time()) + 180
    return jsonify({"c_nonce": c_nonce})

def _require_bearer():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    info = ACCESS_TOKENS.get(token)
    if not info or info["expires"] < int(time.time()):
        return None
    return token

# ---------------------------------------------------------------------
# Credential (mdoc issuance via pymdoccbor)
# ---------------------------------------------------------------------
def build_mdoc_issuersigned_with_helper(doctype: str, data: dict, device_cose_key: dict) -> bytes:
    """
    Use pymdoccbor to construct IssuerSigned and embed an X.509 (x5chain).
    Returns CBOR(IssuerSigned).
    """
    today = datetime.date.today()
    validity = {
        "issuance_date": today.isoformat(),
        "expiry_date": (today.replace(year=today.year + 1)).isoformat()
    }

    # 1) make a self-signed DS cert (DER) for demo
    der = _selfsigned_cert_der_ec(_crypto_priv)
    cert_path = _write_temp_der(der)

    # 2) build with pymdoccbor (will include x5chain from cert_path)
    issuer = MdocCborIssuer(private_key=ISSUER_PKEY, alg="ES256")
    issuer.new(
        doctype=doctype,
        data=data,                         # {"namespace": {...}}
        devicekeyinfo=device_cose_key,     # COSE_Key (int labels)
        validity=validity,
        cert_path=cert_path                # required by current pymdoccbor to embed x5chain
    )

    # 3) dump IssuerSigned (some versions use dump_issuersigned, others dump)
    dump_issuersigned = getattr(issuer, "dump_issuersigned", None)
    result = dump_issuersigned() if callable(dump_issuersigned) else issuer.dump()
    return result

@app.post("/credential")
def credential():
    if _require_bearer() is None:
        return jsonify({"error": "invalid_token"}), 401

    body = request.get_json(force=True, silent=True) or {}
    cfg_id = body.get("credential_configuration_id")
    proofs = (body.get("proofs") or {}).get("jwt") or []
    if cfg_id != CONFIG_ID:
        return jsonify({"error": "unsupported_credential_configuration_id"}), 400
    if not proofs:
        return jsonify({"error": "invalid_request", "error_description": "missing proofs.jwt"}), 400

    holder_jwk, _claims = verify_jwt_proof(proofs[0], aud=ISSUER)
    device_cose_key = jwk_to_cose_ec2_map(holder_jwk)

    data = {
        "org.iso.18013.5.1": {
            "given_name": "Erika",
            "family_name": "Mustermann",
            "birth_date": "1990-01-01",
        }
    }

    issuer_signed_bytes = build_mdoc_issuersigned_with_helper(
        doctype="org.iso.18013.5.1.mDL",
        data=data,
        device_cose_key=device_cose_key
    )
    return jsonify({"credentials": [{
        "format": "mso_mdoc",
        "credential": b64url(issuer_signed_bytes)
    }]})

# ---------------------------------------------------------------------
# Simple verifier UI (manual sanity check)
# ---------------------------------------------------------------------
VERIFY_HTML = """
<!doctype html><title>mdoc verifier</title>
<h1>Paste base64url(CBOR(IssuerSigned))</h1>
<form method="post">
  <textarea name="cred" rows="10" cols="100"></textarea><br/>
  <button>Verify</button>
</form>
{% if result %}
  <h2>Result</h2>
  <pre>{{ result }}</pre>
{% endif %}
"""

@app.route("/verify", methods=["GET", "POST"])
def verify():
    result = None
    if request.method == "POST":
        try:
            cred_b64 = request.form.get("cred", "").strip()
            verifier = request.form.get("verifier", "Web-Verifier")
            
            start_time = time.time()
            raw = b64url_decode_to_bytes(cred_b64)

            # Load, deep-untag, and normalize to an IssuerSigned dict
            decoded_any = _untag_deep(cbor2.loads(raw))
            issuer_signed = _extract_issuersigned(decoded_any)

            # issuerAuth -> COSE_Sign1
            issuer_auth = issuer_signed["issuerAuth"]
            sign1 = _sign1_from_issuer_auth(issuer_auth)
            mso = cbor2.loads(sign1.payload)
            sign1.key = _ISSUER_VERIFY_KEY
            sig_ok = sign1.verify_signature()

            # Verify digests with normalized namespace keys and deep-untagged bytes
            ns_map = _norm_ns_keys(issuer_signed["nameSpaces"])      # { ns: [bstr,...] }
            vd_all = _norm_ns_keys(mso["valueDigests"]["nameSpaces"])# { ns: {digestID: digest} }

            dig_ok = True
            for ns, items in ns_map.items():
                vd_ns = vd_all.get(ns)
                if vd_ns is None:
                    dig_ok = False
                    break
                for item_b in items:
                    b = _as_bytes(item_b)           # deep-untag -> bytes
                    item = cbor2.loads(b)           # IssuerSignedItem
                    want = vd_ns[item["digestID"]]
                    got = hashlib.sha256(b).digest()
                    if want != got:
                        dig_ok = False
                        break
                if not dig_ok:
                    break

            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)
            
            # Determine result
            verification_result = 'PASS' if (sig_ok and dig_ok) else 'FAIL'
            
            # Extract credential ID from mdoc if possible
            credential_id = None
            try:
                doc_type = mso.get("docType", "")
                if doc_type:
                    credential_id = f"EXTRACTED-{doc_type.split('.')[-1]}"
            except:
                pass
            
            # Save verification log to database
            session = get_db_session()
            try:
                # If we have a credential_id, check if it exists in database
                if credential_id:
                    existing_credential = session.query(Credential).filter_by(credential_id=credential_id).first()
                    if not existing_credential:
                        # Create a placeholder credential if it doesn't exist
                        placeholder_credential = Credential(
                            credential_id=credential_id,
                            type='Unknown',
                            format='ISO mdoc',
                            status='active',
                            issued=datetime.datetime.now()
                        )
                        session.add(placeholder_credential)
                        session.commit()
                
                # Create verification log
                verification_log = VerificationLog(
                    credential_id=credential_id or 'UNKNOWN',
                    result=verification_result,
                    response_time=response_time,
                    verifier=verifier,
                    checked_at=datetime.datetime.now()
                )
                session.add(verification_log)
                session.commit()
                
            except Exception as db_error:
                session.rollback()
                print(f"Database error during verification log save: {db_error}")
                # Continue with verification even if database save fails
            
            finally:
                session.close()

            result = json.dumps({
                "docType": mso.get("docType"),
                "validityInfo": mso.get("validityInfo"),
                "signature_valid": bool(sig_ok),
                "digests_valid": bool(dig_ok),
                "verification_result": verification_result,
                "response_time_ms": response_time,
                "verifier": verifier,
                "namespaces": { ns: [cbor2.loads(_as_bytes(b))["elementIdentifier"] for b in items]
                                for ns, items in ns_map.items() }
            }, indent=2)
        except Exception as e:
            # Save failed verification log
            response_time = int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
            session = get_db_session()
            try:
                verification_log = VerificationLog(
                    credential_id='UNKNOWN',
                    result='FAIL',
                    response_time=response_time,
                    verifier=request.form.get("verifier", "Web-Verifier"),
                    checked_at=datetime.datetime.now()
                )
                session.add(verification_log)
                session.commit()
            except Exception as db_error:
                session.rollback()
                print(f"Database error during failed verification log save: {db_error}")
            finally:
                session.close()
            
            result = f"Verification failed: {e}"
    return render_template_string(VERIFY_HTML, result=result)

# ---------------------------------------------------------------------
# Database Dashboard
# ---------------------------------------------------------------------
DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
    <title>OIDC Database Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .section h2 { margin-top: 0; color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .status-active { color: green; font-weight: bold; }
        .status-revoked { color: red; font-weight: bold; }
        .result-pass { color: green; font-weight: bold; }
        .result-fail { color: red; font-weight: bold; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-box { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
        .refresh-btn { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        .refresh-btn:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OIDC Database Dashboard</h1>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{{ stats.total_credentials }}</div>
                <div>Total Credentials</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.active_credentials }}</div>
                <div>Active Credentials</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.total_verifications }}</div>
                <div>Total Verifications</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.successful_verifications }}</div>
                <div>Successful Verifications</div>
            </div>
        </div>

        <button class="refresh-btn" onclick="location.reload()">Refresh Data</button>

        <div class="section">
            <h2>Credentials</h2>
            <table>
                <thead>
                    <tr>
                        <th>Credential ID</th>
                        <th>Subject ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Issued</th>
                        <th>Expires</th>
                    </tr>
                </thead>
                <tbody>
                    {% for cred in credentials %}
                    <tr>
                        <td>{{ cred.credential_id }}</td>
                        <td>{{ cred.subject_id or '-' }}</td>
                        <td>{{ cred.type }}</td>
                        <td class="status-{{ cred.status }}">{{ cred.status }}</td>
                        <td>{{ cred.issued }}</td>
                        <td>{{ cred.expires or 'Never' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Verification Logs</h2>
            <table>
                <thead>
                    <tr>
                        <th>Checked At</th>
                        <th>Credential ID</th>
                        <th>Result</th>
                        <th>Response Time</th>
                        <th>Verifier</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in verification_logs %}
                    <tr>
                        <td>{{ log.checked_at }}</td>
                        <td>{{ log.credential_id }}</td>
                        <td class="result-{{ log.result.lower() }}">{{ log.result }}</td>
                        <td>{{ log.response_time }}ms</td>
                        <td>{{ log.verifier }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route("/dashboard")
def dashboard():
    """Database dashboard showing credentials and verification logs"""
    try:
        session = get_db_session()
        
        # Get credentials
        credentials = session.query(Credential).all()
        
        # Get verification logs
        verification_logs = session.query(VerificationLog).order_by(VerificationLog.checked_at.desc()).limit(20).all()
        
        # Calculate stats
        total_credentials = len(credentials)
        active_credentials = len([c for c in credentials if c.status == 'active'])
        total_verifications = session.query(VerificationLog).count()
        successful_verifications = session.query(VerificationLog).filter_by(result='PASS').count()
        
        stats = {
            'total_credentials': total_credentials,
            'active_credentials': active_credentials,
            'total_verifications': total_verifications,
            'successful_verifications': successful_verifications
        }
        
        return render_template_string(DASHBOARD_HTML, 
                                    credentials=credentials,
                                    verification_logs=verification_logs,
                                    stats=stats)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

# ---------------------------------------------------------------------
# Metrics API Endpoint
# ---------------------------------------------------------------------
@app.route('/api/metrics', methods=['GET', 'OPTIONS'])
def get_metrics():
    """Get dashboard metrics calculated from database"""
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        session = get_db_session()
        
        # Get total credentials
        total_credentials = session.query(Credential).count()
        
        # Get active credentials
        active_credentials = session.query(Credential).filter_by(status='active').count()
        
        # Get new credentials (issued in last 30 days)
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        new_credentials = session.query(Credential).filter(Credential.issued >= thirty_days_ago).count()
        
        # Get total verifications
        total_verifications = session.query(VerificationLog).count()
        
        # Get successful verifications
        successful_verifications = session.query(VerificationLog).filter_by(result='PASS').count()
        
        # Calculate pass rate
        pass_rate = 0.0
        if total_verifications > 0:
            pass_rate = (successful_verifications / total_verifications) * 100
        
        # Calculate fail rate
        fail_rate = 100.0 - pass_rate
        
        # Calculate average response time
        avg_response_time = session.query(VerificationLog.response_time).filter(VerificationLog.response_time.isnot(None)).all()
        avg_response_time = sum([log[0] for log in avg_response_time]) / len(avg_response_time) if avg_response_time else 0
        
        # Calculate metrics for last 30 days vs previous 30 days for change indicators
        sixty_days_ago = datetime.datetime.now() - datetime.timedelta(days=60)
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # Previous 30 days metrics
        prev_verifications = session.query(VerificationLog).filter(
            VerificationLog.checked_at >= sixty_days_ago,
            VerificationLog.checked_at < thirty_days_ago
        ).count()
        
        prev_successful = session.query(VerificationLog).filter(
            VerificationLog.checked_at >= sixty_days_ago,
            VerificationLog.checked_at < thirty_days_ago,
            VerificationLog.result == 'PASS'
        ).count()
        
        prev_pass_rate = (prev_successful / prev_verifications * 100) if prev_verifications > 0 else 0
        
        # Calculate changes
        pass_rate_change = pass_rate - prev_pass_rate
        fail_rate_change = (100 - pass_rate) - (100 - prev_pass_rate)
        
        # Previous average response time
        prev_avg_response = session.query(VerificationLog.response_time).filter(
            VerificationLog.checked_at >= sixty_days_ago,
            VerificationLog.checked_at < thirty_days_ago,
            VerificationLog.response_time.isnot(None)
        ).all()
        prev_avg_response = sum([log[0] for log in prev_avg_response]) / len(prev_avg_response) if prev_avg_response else 0
        
        avg_response_time_change = avg_response_time - prev_avg_response
        
        # Format change indicators
        pass_rate_change_str = f"{'+' if pass_rate_change >= 0 else ''}{pass_rate_change:.1f}%"
        fail_rate_change_str = f"{'+' if fail_rate_change >= 0 else ''}{fail_rate_change:.1f}%"
        avg_response_time_change_str = f"{'+' if avg_response_time_change >= 0 else ''}{int(avg_response_time_change)}ms"
        
        metrics = {
            'success': True,
            'data': {
                'activeCredentials': active_credentials,
                'newCredentials': new_credentials,
                'totalVerifications': total_verifications,
                'passRate': round(pass_rate, 1),
                'failRate': round(fail_rate, 1),
                'avgResponseTime': int(avg_response_time),
                'passRateChange': pass_rate_change_str,
                'failRateChange': fail_rate_change_str,
                'avgResponseTimeChange': avg_response_time_change_str
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Failed to calculate metrics: {str(e)}'
        }), 500
    finally:
        session.close()

# ---------------------------------------------------------------------
# Issue Credential API (for Angular frontend)
# ---------------------------------------------------------------------
@app.route("/api/issue_credential", methods=["POST", "OPTIONS"])
def issue_credential():
    """Issue a new credential and save to database"""
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['credential_id', 'type', 'subject_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False, 
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Resolve subject details from account_id if provided (fake data or random)
        account_id = data.get('account_id')
        resolved_first_name = None
        resolved_last_name = None
        resolved_birth_date = None
        if account_id:
            FAKE_ACCOUNTS = {
                'ACC-123456': { 'given_name': 'Alice', 'family_name': 'Nguyen', 'birth_date': '1991-05-12' },
                'ACC-654321': { 'given_name': 'Bob', 'family_name': 'Martinez', 'birth_date': '1988-11-03' },
                'ACC-777777': { 'given_name': 'Charlie', 'family_name': 'Khan', 'birth_date': '1995-02-25' },
                'ACC-888888': { 'given_name': 'Diana', 'family_name': 'Rossi', 'birth_date': '1993-07-19' },
            }
            details = FAKE_ACCOUNTS.get(account_id)
            if not details:
                # Random fallback
                import random
                samples = [
                    { 'given_name': 'Evan', 'family_name': 'Kim', 'birth_date': '1990-09-09' },
                    { 'given_name': 'Fatima', 'family_name': 'Hassan', 'birth_date': '1992-04-21' },
                    { 'given_name': 'George', 'family_name': 'Ivanov', 'birth_date': '1987-12-30' },
                    { 'given_name': 'Hana', 'family_name': 'Yamamoto', 'birth_date': '1996-03-14' },
                ]
                details = random.choice(samples)
            resolved_first_name = details['given_name']
            resolved_last_name = details['family_name']
            resolved_birth_date = details['birth_date']  # YYYY-MM-DD
        
        # Generate holder key pair
        holder_priv = ec.generate_private_key(ec.SECP256R1())
        holder_pub = holder_priv.public_key().public_numbers()
        holder_jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(holder_pub.x.to_bytes(32, "big")).rstrip(b"=").decode(),
            "y": base64.urlsafe_b64encode(holder_pub.y.to_bytes(32, "big")).rstrip(b"=").decode(),
            "kid": f"holder-{data['credential_id']}"
        }

        # Get nonce
        nonce = secrets.token_urlsafe(24)
        NONCES[nonce] = int(time.time()) + 180

        # Create proof JWT
        proof_header = {"typ": "openid4vci-proof+jwt", "alg": ALG_JOSE, "jwk": holder_jwk}
        proof_payload = {
            "iss": "demo-holder",
            "aud": ISSUER,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "nonce": nonce
        }
        proof_jwt = jwt.encode(proof_payload, holder_priv, algorithm=ALG_JOSE, headers=proof_header)

        # Build mdoc data with user-provided or resolved information
        given_name = data.get('given_name') or resolved_first_name or 'John'
        family_name = data.get('family_name') or resolved_last_name or 'Doe'
        birth_date = data.get('birth_date') or resolved_birth_date or '1990-01-01'
        mdoc_data = {
            "org.iso.18013.5.1": {
                "given_name": given_name,
                "family_name": family_name,
                "birth_date": birth_date,
            }
        }

        # Add custom fields if provided, and include account_id for traceability
        if 'custom_fields' in data and isinstance(data['custom_fields'], dict):
            mdoc_data["org.iso.18013.5.1"].update(data['custom_fields'])
        if account_id:
            mdoc_data["org.iso.18013.5.1"]["account_id"] = account_id

        # Generate mdoc credential using pymdoccbor
        device_cose_key = jwk_to_cose_ec2_map(holder_jwk)
        mdoc_bytes = build_mdoc_issuersigned_with_helper(
            "org.iso.18013.5.1.mDL", 
            mdoc_data, 
            device_cose_key
        )
        mdoc_b64url = b64url(mdoc_bytes)
        mdoc_hex = mdoc_bytes.hex()

        # Save credential to database
        session = get_db_session()
        try:
            # Check if credential_id already exists
            existing = session.query(Credential).filter_by(credential_id=data['credential_id']).first()
            if existing:
                return jsonify({
                    'success': False, 
                    'error': 'Credential ID already exists'
                }), 400
            
            # Create credential record
            credential_data = {
                'credential_id': data['credential_id'],
                'subject_id': data.get('subject_id'),
                'type': data['type'],
                'format': data.get('format', 'ISO mdoc'),
                'status': data.get('status', 'active'),
                'issued': datetime.datetime.now(),
                'expires': None
            }
            
            # Parse expiry date if provided
            if 'expires' in data and data['expires']:
                try:
                    credential_data['expires'] = datetime.datetime.fromisoformat(data['expires'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({
                        'success': False, 
                        'error': 'Invalid expiry date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
                    }), 400
            
            credential = Credential(**credential_data)
            session.add(credential)
            session.commit()
            
            # Prepare response
            response_data = {
                'success': True,
                'credential': {
                    'id': credential.id,
                    'credential_id': credential.credential_id,
                    'subject_id': credential.subject_id,
                    'type': credential.type,
                    'format': credential.format,
                    'status': credential.status,
                    'issued': credential.issued.isoformat(),
                    'expires': credential.expires.isoformat() if credential.expires else None
                },
                'mdoc': {
                    'base64url': mdoc_b64url,
                    'hex': mdoc_hex
                },
                'jwk': holder_jwk,
                'proof_jwt': proof_jwt,
                'nonce': nonce
            }
            
            return jsonify(response_data), 201
            
        except Exception as e:
            session.rollback()
            return jsonify({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Credential issuance failed: {str(e)}'
        }), 500

# ---------------------------------------------------------------------
# Enhanced Verification API (saves to database)
# ---------------------------------------------------------------------
@app.route("/api/verify_credential", methods=["POST"])
def verify_credential_api():
    """Verify a credential and save verification log to database"""
    try:
        data = request.get_json()
        
        if not data or 'credential' not in data:
            return jsonify({
                'success': False, 
                'error': 'Missing credential data'
            }), 400
        
        cred_b64 = data['credential'].strip()
        verifier = data.get('verifier', 'API-Verifier')
        
        start_time = time.time()
        
        try:
            raw = b64url_decode_to_bytes(cred_b64)

            # Load, deep-untag, and normalize to an IssuerSigned dict
            decoded_any = _untag_deep(cbor2.loads(raw))
            issuer_signed = _extract_issuersigned(decoded_any)

            # issuerAuth -> COSE_Sign1
            issuer_auth = issuer_signed["issuerAuth"]
            sign1 = _sign1_from_issuer_auth(issuer_auth)
            mso = cbor2.loads(sign1.payload)
            sign1.key = _ISSUER_VERIFY_KEY
            sig_ok = sign1.verify_signature()

            # Verify digests with normalized namespace keys and deep-untagged bytes
            ns_map = _norm_ns_keys(issuer_signed["nameSpaces"])
            vd_all = _norm_ns_keys(mso["valueDigests"]["nameSpaces"])

            dig_ok = True
            for ns, items in ns_map.items():
                vd_ns = vd_all.get(ns)
                if vd_ns is None:
                    dig_ok = False
                    break
                for item_b in items:
                    b = _as_bytes(item_b)
                    item = cbor2.loads(b)
                    want = vd_ns[item["digestID"]]
                    got = hashlib.sha256(b).digest()
                    if want != got:
                        dig_ok = False
                        break
                if not dig_ok:
                    break

            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
            
            # Determine result
            verification_result = 'PASS' if (sig_ok and dig_ok) else 'FAIL'
            
            # Extract credential ID from mdoc if possible
            credential_id = None
            try:
                # Try to extract from docType or other fields
                doc_type = mso.get("docType", "")
                if doc_type:
                    # You might need to adjust this based on your credential structure
                    credential_id = f"EXTRACTED-{doc_type.split('.')[-1]}"
            except:
                pass
            
            # Save verification log to database
            session = get_db_session()
            try:
                # If we have a credential_id, check if it exists in database
                if credential_id:
                    existing_credential = session.query(Credential).filter_by(credential_id=credential_id).first()
                    if not existing_credential:
                        # Create a placeholder credential if it doesn't exist
                        placeholder_credential = Credential(
                            credential_id=credential_id,
                            type='Unknown',
                            format='ISO mdoc',
                            status='active',
                            issued=datetime.datetime.now()
                        )
                        session.add(placeholder_credential)
                        session.commit()
                
                # Create verification log
                verification_log = VerificationLog(
                    credential_id=credential_id or 'UNKNOWN',
                    result=verification_result,
                    response_time=response_time,
                    verifier=verifier,
                    checked_at=datetime.datetime.now()
                )
                session.add(verification_log)
                session.commit()
                
            except Exception as db_error:
                session.rollback()
                print(f"Database error during verification log save: {db_error}")
                # Continue with verification even if database save fails
            
            finally:
                session.close()

            # Prepare verification result
            verification_data = {
                'success': True,
                'verification': {
                    'result': verification_result,
                    'response_time_ms': response_time,
                    'verifier': verifier,
                    'signature_valid': bool(sig_ok),
                    'digests_valid': bool(dig_ok),
                    'docType': mso.get("docType"),
                    'validityInfo': mso.get("validityInfo"),
                    'namespaces': {
                        str(ns): [str(cbor2.loads(_as_bytes(b)).get("elementIdentifier", "")) for b in items]
                        for ns, items in ns_map.items()
                    }
                }
            }
            
            return jsonify(verification_data)
            
        except Exception as verification_error:
            # Calculate response time even for failed verifications
            response_time = int((time.time() - start_time) * 1000)
            
            # Save failed verification log
            session = get_db_session()
            try:
                verification_log = VerificationLog(
                    credential_id='UNKNOWN',
                    result='FAIL',
                    response_time=response_time,
                    verifier=verifier,
                    checked_at=datetime.datetime.now()
                )
                session.add(verification_log)
                session.commit()
            except Exception as db_error:
                session.rollback()
                print(f"Database error during failed verification log save: {db_error}")
            finally:
                session.close()
            
            return jsonify({
                'success': False,
                'error': f'Verification failed: {str(verification_error)}',
                'verification': {
                    'result': 'FAIL',
                    'response_time_ms': response_time,
                    'verifier': verifier
                }
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Verification request failed: {str(e)}'
        }), 500

# ---------------------------------------------------------------------
# Revoke Credential API
# ---------------------------------------------------------------------
@app.route("/api/revoke", methods=["POST", "OPTIONS"])
def revoke_credential():
    """Revoke a credential by changing its status to revoked"""
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        if not data or 'credential_id' not in data:
            return jsonify({
                'success': False, 
                'error': 'Missing credential_id'
            }), 400
        
        credential_id = data['credential_id']
        reason = data.get('reason', 'No reason provided')
        
        # Get database session
        session = get_db_session()
        try:
            # Find the credential
            credential = session.query(Credential).filter_by(credential_id=credential_id).first()
            
            if not credential:
                return jsonify({
                    'success': False, 
                    'error': f'Credential with ID {credential_id} not found'
                }), 404
            
            # Check if already revoked
            if credential.status == 'revoked':
                return jsonify({
                    'success': False, 
                    'error': f'Credential {credential_id} is already revoked'
                }), 400
            
            # Update status to revoked
            credential.status = 'revoked'
            
            session.commit()
            
            # Prepare response
            response_data = {
                'success': True,
                'message': f'Credential {credential_id} revoked successfully',
                'credential': {
                    'id': credential.id,
                    'credential_id': credential.credential_id,
                    'subject_id': credential.subject_id,
                    'type': credential.type,
                    'format': credential.format,
                    'status': credential.status,
                    'issued': credential.issued.isoformat(),
                    'expires': credential.expires.isoformat() if credential.expires else None
                },
                'revocation_info': {
                    'revoked_at': datetime.datetime.now().isoformat(),
                    'reason': reason
                }
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            session.rollback()
            return jsonify({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Revocation request failed: {str(e)}'
        }), 500

# ---------------------------------------------------------------------
# Extend Credential Expiry API
# ---------------------------------------------------------------------
@app.route("/api/extend_expiry_date", methods=["POST", "OPTIONS"])
def extend_credential_expiry():
    """Extend the expiry date of a credential"""
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        
        if not data or 'credential_id' not in data:
            return jsonify({
                'success': False, 
                'error': 'Missing credential_id'
            }), 400
        
        if 'new_expiry_date' not in data:
            return jsonify({
                'success': False, 
                'error': 'Missing new_expiry_date'
            }), 400
        
        credential_id = data['credential_id']
        new_expiry_date_str = data['new_expiry_date']
        reason = data.get('reason', 'Extended by user request')
        
        # Parse the new expiry date
        try:
            new_expiry_date = datetime.datetime.fromisoformat(new_expiry_date_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False, 
                'error': 'Invalid expiry date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
            }), 400
        
        # Validate that new expiry date is in the future
        current_time = datetime.datetime.now(new_expiry_date.tzinfo if new_expiry_date.tzinfo else None)
        if new_expiry_date <= current_time:
            return jsonify({
                'success': False, 
                'error': 'New expiry date must be in the future'
            }), 400
        
        # Get database session
        session = get_db_session()
        try:
            # Find the credential
            credential = session.query(Credential).filter_by(credential_id=credential_id).first()
            
            if not credential:
                return jsonify({
                    'success': False, 
                    'error': f'Credential with ID {credential_id} not found'
                }), 404
            
            # Check if credential is revoked
            if credential.status == 'revoked':
                return jsonify({
                    'success': False, 
                    'error': f'Cannot extend expiry date of revoked credential {credential_id}'
                }), 400
            
            # Store the old expiry date for response
            old_expiry_date = credential.expires
            
            # Update the expiry date
            credential.expires = new_expiry_date
            
            # If credential was expired, change status back to active
            if credential.status == 'expired':
                credential.status = 'active'
            
            session.commit()
            
            # Prepare response
            response_data = {
                'success': True,
                'message': f'Credential {credential_id} expiry date extended successfully',
                'credential': {
                    'id': credential.id,
                    'credential_id': credential.credential_id,
                    'subject_id': credential.subject_id,
                    'type': credential.type,
                    'format': credential.format,
                    'status': credential.status,
                    'issued': credential.issued.isoformat(),
                    'expires': credential.expires.isoformat() if credential.expires else None
                },
                'extension_info': {
                    'old_expiry_date': old_expiry_date.isoformat() if old_expiry_date else None,
                    'new_expiry_date': new_expiry_date.isoformat(),
                    'extended_at': datetime.datetime.now().isoformat(),
                    'reason': reason
                }
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            session.rollback()
            return jsonify({
                'success': False, 
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Extension request failed: {str(e)}'
        }), 500

# ---------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers"""
    try:
        # Check database connection
        session = get_db_session()
        session.execute("SELECT 1")
        session.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'oidc-backend',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'service': 'oidc-backend',
            'error': str(e)
        }), 503

# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Demo only (no TLS). Use HTTPS + real hostname in production.
    app.run(host="0.0.0.0", port=5000, debug=True) 