from flask import Flask, request, jsonify, render_template_string
import base64, cbor2, datetime, hashlib, os, secrets, time, json
from cbor2 import CBORTag

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

app = Flask(__name__)

# ---------------------------------------------------------------------
# Config (demo)
# ---------------------------------------------------------------------
ISSUER = "https://issuer.example.com"          # Credential Issuer Identifier
CONFIG_ID = "org.iso.18013.5.1.mDL"            # supported configuration id
ALG_COSE = -7                                  # ES256 (COSE numeric)
ALG_JOSE = "ES256"                             # ES256 (JOSE string)

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

            result = json.dumps({
                "docType": mso.get("docType"),
                "validityInfo": mso.get("validityInfo"),
                "signature_valid": bool(sig_ok),
                "digests_valid": bool(dig_ok),
                "namespaces": { ns: [cbor2.loads(_as_bytes(b))["elementIdentifier"] for b in items]
                                for ns, items in ns_map.items() }
            }, indent=2)
        except Exception as e:
            result = f"Verification failed: {e}"
    return render_template_string(VERIFY_HTML, result=result)

# ---------------------------------------------------------------------
# One-click demo page (runs offer→token→nonce→proof→credential locally)
# ---------------------------------------------------------------------
REQUEST_CREDENTIAL_HTML = """
<!doctype html><title>Request mdoc (demo)</title>
<h1>OpenID4VCI mdoc demo (pymdoccbor)</h1>
<form method="post">
  <button>Run demo flow (offer → token → nonce → proof → credential)</button>
</form>
{% if out %}
  <h2>Outputs</h2>
  <h3>Offer</h3><pre>{{ out.offer }}</pre>
  <h3>Access Token</h3><pre>{{ out.token }}</pre>
  <h3>c_nonce</h3><pre>{{ out.c_nonce }}</pre>
  <h3>Proof JWT</h3><pre>{{ out.proof }}</pre>
  <h3>Credential (base64url)</h3>
  <pre>{{ out.cred }}</pre>
  <p>Paste in <a href="/verify" target="_blank">/verify</a></p>
{% endif %}
"""

@app.route("/request_credential", methods=["GET", "POST"])
def request_credential():
    out = None
    if request.method == "POST":
        # 1) Offer
        code = secrets.token_urlsafe(24)
        PRE_AUTH_CODES[code] = {"config_id": CONFIG_ID, "created": int(time.time())}
        offer = {
            "credential_issuer": ISSUER,
            "credential_configuration_ids": [CONFIG_ID],
            "grants": {"urn:ietf:params:oauth:grant-type:pre-authorized_code": {"pre-authorized_code": code}}
        }
        # 2) Token
        access_token = secrets.token_urlsafe(32)
        ACCESS_TOKENS[access_token] = {"expires": int(time.time()) + 600}
        # 3) Nonce
        c_nonce = secrets.token_urlsafe(24)
        NONCES[c_nonce] = int(time.time()) + 180
        # 4) Proof
        holder_priv = ec.generate_private_key(ec.SECP256R1())
        holder_pub = holder_priv.public_key().public_numbers()
        holder_jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(holder_pub.x.to_bytes(32, "big")).rstrip(b"=").decode(),
            "y": base64.urlsafe_b64encode(holder_pub.y.to_bytes(32, "big")).rstrip(b"=").decode(),
            "kid": "demo-holder"
        }
        proof_header = {"typ": "openid4vci-proof+jwt", "alg": ALG_JOSE, "jwk": holder_jwk}
        now = int(time.time())
        proof_payload = {"iss": "demo-holder", "aud": ISSUER, "iat": now, "exp": now + 300, "nonce": c_nonce}
        proof_jwt = jwt.encode(proof_payload, holder_priv, algorithm=ALG_JOSE, headers=proof_header)
        # 5) Credential (internal call to builder)
        device_cose_key = jwk_to_cose_ec2_map(holder_jwk)
        data = {"org.iso.18013.5.1": {"given_name": "Erika", "family_name": "Mustermann", "birth_date": "1990-01-01"}}
        cred_b64 = b64url(build_mdoc_issuersigned_with_helper("org.iso.18013.5.1.mDL", data, device_cose_key))

        out = {
            "offer": json.dumps({"credential_offer": offer}, indent=2),
            "token": json.dumps({"access_token": access_token, "token_type": "Bearer", "expires_in": 600}, indent=2),
            "c_nonce": c_nonce,
            "proof": proof_jwt,
            "cred": cred_b64
        }
    return render_template_string(REQUEST_CREDENTIAL_HTML, out=out)

# ---------------------------------------------------------------------
# Form-based credential request page
# ---------------------------------------------------------------------
FORM_CREDENTIAL_HTML = """
<!doctype html>
<html>
<head>
    <title>Request mdoc Credential</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .step { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .step h3 { margin-top: 0; color: #333; }
        .success { background-color: #d4edda; border-color: #c3e6cb; }
        .error { background-color: #f8d7da; border-color: #f5c6cb; }
        .info { background-color: #d1ecf1; border-color: #bee5eb; }
        pre { background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        .credential-display { word-break: break-all; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="date"] { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; box-sizing: border-box; }
        .form-row { display: flex; gap: 15px; }
        .form-row .form-group { flex: 1; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Request mdoc Credential</h1>
        
        {% if not result %}
        <div class="step info">
            <h3>📝 Fill in Your Bank Account Details</h3>
            <p>Please provide your bank account information to issue your mdoc credential:</p>
        </div>

        <div class="step">
            <form method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label for="account_holder_name">Account Holder Name *</label>
                        <input type="text" id="account_holder_name" name="account_holder_name" value="{{ form_data.account_holder_name or '' }}" required>
                    </div>
                    <div class="form-group">
                        <label for="account_number">Account Number *</label>
                        <input type="text" id="account_number" name="account_number" value="{{ form_data.account_number or '' }}" required>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="account_type">Account Type *</label>
                        <select id="account_type" name="account_type" required>
                            <option value="">Select Account Type</option>
                            <option value="Savings" {% if form_data.account_type == 'Savings' %}selected{% endif %}>Savings</option>
                            <option value="Checking" {% if form_data.account_type == 'Checking' %}selected{% endif %}>Checking</option>
                            <option value="Current" {% if form_data.account_type == 'Current' %}selected{% endif %}>Current</option>
                            <option value="Investment" {% if form_data.account_type == 'Investment' %}selected{% endif %}>Investment</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="currency">Currency *</label>
                        <select id="currency" name="currency" required>
                            <option value="">Select Currency</option>
                            <option value="NZD" {% if form_data.currency == 'NZD' %}selected{% endif %}>NZD (NZ Dollar)</option>
                            <option value="USD" {% if form_data.currency == 'USD' %}selected{% endif %}>USD (US Dollar)</option>
                            <option value="EUR" {% if form_data.currency == 'EUR' %}selected{% endif %}>EUR (Euro)</option>
                            <option value="GBP" {% if form_data.currency == 'GBP' %}selected{% endif %}>GBP (British Pound)</option>
                            <option value="JPY" {% if form_data.currency == 'JPY' %}selected{% endif %}>JPY (Japanese Yen)</option>
                            <option value="CAD" {% if form_data.currency == 'CAD' %}selected{% endif %}>CAD (Canadian Dollar)</option>
                            <option value="AUD" {% if form_data.currency == 'AUD' %}selected{% endif %}>AUD (Australian Dollar)</option>
                        </select>
                    </div>
                </div>
                
                <button type="submit">Request Bank Account Credential</button>
            </form>
        </div>
        {% else %}
        
        <div class="step success">
            <h3>✅ Bank Account Credential Issued Successfully!</h3>
            <p>The bank account mdoc credential has been generated successfully with ISO 18013-5 compliant format.</p>
        </div>

        <div class="step">
            <h3>🏦 Bank Account Information Used</h3>
            <pre>{{ result.personal_info | tojson(indent=2) }}</pre>
        </div>

        <div class="step">
            <h3>📋 Generated JWK</h3>
            <pre>{{ result.jwk | tojson(indent=2) }}</pre>
        </div>

        <div class="step">
            <h3>🔢 Nonce</h3>
            <pre>{{ result.nonce }}</pre>
        </div>

        <div class="step">
            <h3>🔐 Proof JWT</h3>
            <pre class="credential-display">{{ result.proof_jwt }}</pre>
        </div>

        <div class="step">
            <h3>🎫 mdoc Credential (base64url)</h3>
            
            <pre class="credential-display">{{ result.mdoc_b64url }}</pre>
        </div>

        <div class="step">
            <h3>🎫 mdoc Credential (hex)</h3>
            
            <pre class="credential-display">{{ result.mdoc_hex }}</pre>
        </div>

        <div class="step">
            <h3>🔄 Try Again</h3>
            <form method="POST">
                <button type="submit">Request Another Credential</button>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/form_credential", methods=["GET", "POST"])
def form_credential():
    """Form-based credential request endpoint"""
    if request.method == "GET":
        default_form_data = {
            "account_holder_name": "",
            "account_number": "",
            "account_type": "",
            "currency": ""
        }
        return render_template_string(FORM_CREDENTIAL_HTML, form_data=default_form_data)

    # Get form data
    form_data = {
        "account_holder_name": request.form.get("account_holder_name", ""),
        "account_number": request.form.get("account_number", ""),
        "account_type": request.form.get("account_type", ""),
        "currency": request.form.get("currency", "")
    }

    if not form_data["account_holder_name"] or not form_data["account_number"] or not form_data["account_type"] or not form_data["currency"]:
        return render_template_string(
            FORM_CREDENTIAL_HTML,
            form_data=form_data,
            result={"error": "Please fill in all required fields (Account Holder Name, Account Number, Account Type, and Currency)"}
        )

    try:
        # 1. Generate holder key pair
        holder_priv = ec.generate_private_key(ec.SECP256R1())
        holder_pub = holder_priv.public_key().public_numbers()
        holder_jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": base64.urlsafe_b64encode(holder_pub.x.to_bytes(32, "big")).rstrip(b"=").decode(),
            "y": base64.urlsafe_b64encode(holder_pub.y.to_bytes(32, "big")).rstrip(b"=").decode(),
            "kid": "demo-holder"
        }

        # 2. Get nonce
        nonce = secrets.token_urlsafe(24)
        NONCES[nonce] = int(time.time()) + 180

        # 3. Create proof JWT
        proof_header = {"typ": "openid4vci-proof+jwt", "alg": ALG_JOSE, "jwk": holder_jwk}
        proof_payload = {
            "iss": "demo-holder",
            "aud": ISSUER,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "nonce": nonce
        }
        proof_jwt = jwt.encode(proof_payload, holder_priv, algorithm=ALG_JOSE, headers=proof_header)

        # 4. Build mdoc data with user-provided information
        data = {
            "org.iso.18013.5.1": {
                "account_holder_name": form_data["account_holder_name"],
                "account_number": form_data["account_number"],
                "account_type": form_data["account_type"],
                "currency": form_data["currency"]
            }
        }

        # 5. Generate mdoc credential using pymdoccbor (IssuerSigned CBOR)
        device_cose_key = jwk_to_cose_ec2_map(holder_jwk)
        mdoc_bytes = build_mdoc_issuersigned_with_helper("org.example.bank.account", data, device_cose_key)
        mdoc_b64url = b64url(mdoc_bytes)
        mdoc_hex = mdoc_bytes.hex()  # Convert to hex string

        # 6. Verification (single normalized path)
        try:
            raw = b64url_decode_to_bytes(mdoc_b64url)
            decoded = _untag_deep(cbor2.loads(raw))
            
            # Debug: Print the structure we're working with
            print("DEBUG: decoded type after _untag_deep:", type(decoded))
            if isinstance(decoded, dict):
                print("DEBUG: decoded keys:", list(decoded.keys()))
            elif isinstance(decoded, list):
                print("DEBUG: decoded is list with length:", len(decoded))
                if len(decoded) > 0:
                    print("DEBUG: first element type:", type(decoded[0]))

            # normalize to IssuerSigned dict
            issuer_signed = _extract_issuersigned(decoded)
            print("DEBUG: issuer_signed type:", type(issuer_signed))
            if isinstance(issuer_signed, dict):
                print("DEBUG: issuer_signed keys:", list(issuer_signed.keys()))

            # issuerAuth -> Sign1
            issuer_auth = issuer_signed["issuerAuth"]
            print("DEBUG: issuer_auth type:", type(issuer_auth))
            if isinstance(issuer_auth, CBORTag):
                print("DEBUG: issuer_auth is CBORTag with tag:", issuer_auth.tag)
                print("DEBUG: issuer_auth.value type:", type(issuer_auth.value))
            
            sign1 = _sign1_from_issuer_auth(issuer_auth)
            mso = cbor2.loads(sign1.payload)
            sign1.key = _ISSUER_VERIFY_KEY
            sig_ok = sign1.verify_signature()

            # Verify digests
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

            verification = {
                "docType": str(mso.get("docType", "")),
                "validityInfo": mso.get("validityInfo"),
                "signature_valid": bool(sig_ok),
                "digests_valid": bool(dig_ok),
                "structure": "IssuerSigned (normalized)",
                "namespaces": {
                    str(ns): [str(cbor2.loads(_as_bytes(b)).get("elementIdentifier", "")) for b in items]
                    for ns, items in ns_map.items()
                }
            }

        except Exception as e:
            verification = {"error": str(e)}

        result = {
            "personal_info": form_data,
            "jwk": holder_jwk,
            "nonce": nonce,
            "proof_jwt": proof_jwt,
            "mdoc_b64url": mdoc_b64url,
            "mdoc_hex": mdoc_hex, # Add hex string to result
            "verification": verification
        }

        return render_template_string(FORM_CREDENTIAL_HTML, result=result)

    except Exception as e:
        return render_template_string(FORM_CREDENTIAL_HTML, form_data=form_data, result={"error": str(e)})

# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Demo only (no TLS). Use HTTPS + real hostname in production.
    app.run(host="0.0.0.0", port=5000, debug=True)
