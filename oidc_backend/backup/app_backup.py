from flask import Flask, request, jsonify, render_template_string
import base64, cbor2, datetime, hashlib, os, secrets, time, json, typing as t

import jwt  # PyJWT
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

# pycose (COSE)
from pycose.messages import Sign1Message
from pycose.headers import Algorithm
from pycose.algorithms import Es256
from pycose.keys.ec2 import EC2Key
from pycose.keys.curves import P256

app = Flask(__name__)

# ---------------------------------------------------------------------
# Config (demo)
# ---------------------------------------------------------------------
ISSUER = "https://issuer.example.com"  # Credential Issuer Identifier
CONFIG_ID = "org.iso.18013.5.1.mDL"    # our single supported profile ID
ALG_COSE = -7                          # ES256 in COSE numeric form
ALG_JOSE = "ES256"                     # ES256 in JOSE string form

# In-memory stores (use Redis/DB in production)
PRE_AUTH_CODES: dict[str, dict] = {}   # code -> {"config_id": str, "created": int}
ACCESS_TOKENS: dict[str, dict] = {}    # token -> {"expires": int, "used": bool}
NONCES: dict[str, int] = {}            # c_nonce -> expires_at (unix time)

# ---------------------------------------------------------------------
# Demo issuer key (static, don't use in prod)
# We derive pub (x,y) from a fixed private scalar so we can also verify.
# ---------------------------------------------------------------------
ISSUER_D_HEX = "11" * 32  # 32 bytes (256-bit) demo scalar
_issuer_d_int = int(ISSUER_D_HEX, 16)
_crypto_priv = ec.derive_private_key(_issuer_d_int, ec.SECP256R1())
_crypto_pub = _crypto_priv.public_key()
_pub_nums = _crypto_pub.public_numbers()
_ISSUER_X = _pub_nums.x.to_bytes(32, "big")
_ISSUER_Y = _pub_nums.y.to_bytes(32, "big")
_ISSUER_D = _issuer_d_int.to_bytes(32, "big")

# pycose keys: one for signing (has d), one for verifying (x,y)
_ISSUER_SIGN_KEY = EC2Key(crv=P256, x=_ISSUER_X, y=_ISSUER_Y, d=_ISSUER_D)
_ISSUER_VERIFY_KEY = EC2Key(crv=P256, x=_ISSUER_X, y=_ISSUER_Y)  # no d

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def b64url_decode_to_bytes(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)

def jwk_to_cose_ec2_map(jwk: dict) -> dict:
    """Return a COSE_Key (CBOR map) using integer labels, as required by ISO mdoc."""
    def b64u_decode(s: str) -> bytes:
        pad = "=" * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s + pad)
    assert jwk.get("kty") == "EC" and jwk.get("crv") in ("P-256", "secp256r1")
    x = b64u_decode(jwk["x"])
    y = b64u_decode(jwk["y"])
    cose_key = {
        1: 2,     # kty: EC2
        -1: 1,    # crv: P-256
        -2: x,    # x-coordinate (bstr)
        -3: y,    # y-coordinate (bstr)
    }
    if jwk.get("kid"):
        cose_key[2] = jwk["kid"].encode()  # kid (optional)
    return cose_key

def verify_jwt_proof(proof_jwt: str, aud: str) -> tuple[dict, dict]:
    """
    Verify the OpenID4VCI proof JWT:
    - header.typ == "openid4vci-proof+jwt"
    - header.jwk present (holder binding)
    - 'aud' matches Credential Issuer Identifier
    - 'nonce' present and valid; consume one-time
    Returns (holder_jwk_dict, claims)
    """
    header = jwt.get_unverified_header(proof_jwt)
    if header.get("typ") != "openid4vci-proof+jwt":
        raise ValueError("invalid proof typ")
    holder_jwk = header.get("jwk")
    if not holder_jwk:
        raise ValueError("missing holder jwk in proof header")

    # Convert holder JWK -> cryptography pub key to verify JOSE signature
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
    # one-time use
    del NONCES[nonce]
    return holder_jwk, claims

def build_mdoc_issuersigned(doctype: str, data: dict, device_cose_key: dict) -> bytes:
    """
    Build ISO 18013-5 IssuerSigned = { nameSpaces, issuerAuth }.
    - nameSpaces: { namespace: [IssuerSignedItemBytes ...] }
    - issuerAuth: COSE_Sign1(MSO)
    MSO includes valueDigests per namespace, deviceKey, docType, validityInfo.
    """
    now = datetime.datetime.utcnow().replace(microsecond=0)
    signed_ts = now.isoformat() + "Z"
    valid_from_ts = signed_ts
    valid_until_ts = (now + datetime.timedelta(days=365)).isoformat() + "Z"

    # 1) Build IssuerSignedItemBytes & digests
    nameSpaces: dict[str, list[bytes]] = {}
    valueDigests: dict[str, dict[int, bytes]] = {}

    for ns, elements in data.items():
        items_bstrs: list[bytes] = []
        digest_map: dict[int, bytes] = {}
        digest_id = 0
        for element_id, element_value in elements.items():
            # Per spec: IssuerSignedItem = {digestID, random, elementIdentifier, elementValue}
            item = {
                "digestID": digest_id,
                "random": os.urandom(16),           # >= 16 bytes salt
                "elementIdentifier": element_id,
                "elementValue": element_value
            }
            item_bytes = cbor2.dumps(item)         # IssuerSignedItemBytes == bstr of CBOR(IssuerSignedItem)
            digest = hashlib.sha256(item_bytes).digest()
            items_bstrs.append(item_bytes)
            digest_map[digest_id] = digest
            digest_id += 1

        nameSpaces[ns] = items_bstrs
        valueDigests[ns] = digest_map

    # 2) MSO (payload of issuerAuth)
    mso = {
        "digestAlgorithm": "SHA-256",
        "valueDigests": {"nameSpaces": valueDigests},
        "deviceKey": device_cose_key,        # COSE_Key (CBOR map with int labels)
        "docType": doctype,
        "validityInfo": {
            "signed": signed_ts,
            "validFrom": valid_from_ts,
            "validUntil": valid_until_ts
        }
    }
    mso_payload = cbor2.dumps(mso)

    # 3) COSE_Sign1 over MSO (ES256, empty external_aad)
    sign1 = Sign1Message(phdr={Algorithm: Es256}, payload=mso_payload, external_aad=b"")
    sign1.key = _ISSUER_SIGN_KEY
    issuer_auth = sign1.encode()

    # 4) Assemble IssuerSigned (top-level object to return as credential)
    issuer_signed = {
        "nameSpaces": nameSpaces,
        "issuerAuth": issuer_auth
    }
    return cbor2.dumps(issuer_signed)

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
                # Optionally: "tx_code": {"length": 6, "input_mode": "numeric"}
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
    # If using tx_code, validate here

    # single-use code
    del PRE_AUTH_CODES[code]

    access_token = secrets.token_urlsafe(32)
    ACCESS_TOKENS[access_token] = {"expires": int(time.time()) + 600, "used": False}
    # Note: c_nonce is NOT returned here (use /nonce in this profile)
    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 600
    })

# ---------------------------------------------------------------------
# Nonce endpoint
# ---------------------------------------------------------------------
@app.post("/nonce")
def nonce():
    c_nonce = secrets.token_urlsafe(24)
    NONCES[c_nonce] = int(time.time()) + 180  # 3 min validity
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
# Credential (mdoc issuance)
# ---------------------------------------------------------------------
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

    # Verify proof JWT (typ, jwk, aud, nonce)
    holder_jwk, _claims = verify_jwt_proof(proofs[0], aud=ISSUER)
    device_cose_key = jwk_to_cose_ec2_map(holder_jwk)

    # Minimal attributes (you can pull from request/DB)
    data = {
        "org.iso.18013.5.1": {
            "given_name": "Erika",
            "family_name": "Mustermann",
            "birth_date": "1990-01-01",
        }
    }

    # Build IssuerSigned and return base64url(CBOR(IssuerSigned))
    issuer_signed_bytes = build_mdoc_issuersigned(
        doctype="org.iso.18013.5.1.mDL",
        data=data,
        device_cose_key=device_cose_key
    )
    return jsonify({"credentials": [{
        "format": "mso_mdoc",
        "credential": b64url(issuer_signed_bytes)
    }]})

# ---------------------------------------------------------------------
# Simple verifier UI (for manual tests)
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
            issuer_signed = cbor2.loads(raw)

            # 1) parse issuerAuth and verify signature over MSO
            issuer_auth = issuer_signed["issuerAuth"]
            sign1 = Sign1Message.decode(issuer_auth)
            mso = cbor2.loads(sign1.payload)
            sign1.key = _ISSUER_VERIFY_KEY
            sig_ok = sign1.verify_signature()

            # 2) recompute digests for each IssuerSignedItemBytes
            ns_map = issuer_signed["nameSpaces"]              # { ns: [bstr, ...] }
            vd = mso["valueDigests"]["nameSpaces"]            # { ns: {digestID: digest} }
            dig_ok = True
            for ns, items in ns_map.items():
                for b in items:
                    item = cbor2.loads(b)
                    want = vd[ns][item["digestID"]]
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
                "namespaces": { ns: [cbor2.loads(b)["elementIdentifier"] for b in items]
                                for ns, items in ns_map.items() }
            }, indent=2)
        except Exception as e:
            result = f"Verification failed: {e}"
    return render_template_string(VERIFY_HTML, result=result)

# ---------------------------------------------------------------------
# Simple end-to-end demo page (simulates holder)
# ---------------------------------------------------------------------
REQUEST_CREDENTIAL_HTML = """
<!doctype html><title>Request mdoc (demo)</title>
<h1>OpenID4VCI mdoc demo</h1>
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
        # 1) Get an offer (pre-authorized code)
        code = secrets.token_urlsafe(24)
        PRE_AUTH_CODES[code] = {"config_id": CONFIG_ID, "created": int(time.time())}
        offer = {
            "credential_issuer": ISSUER,
            "credential_configuration_ids": [CONFIG_ID],
            "grants": {"urn:ietf:params:oauth:grant-type:pre-authorized_code": {"pre-authorized_code": code}}
        }

        # 2) Exchange for token
        access_token = secrets.token_urlsafe(32)
        ACCESS_TOKENS[access_token] = {"expires": int(time.time()) + 600, "used": False}

        # 3) Get c_nonce
        c_nonce = secrets.token_urlsafe(24)
        NONCES[c_nonce] = int(time.time()) + 180

        # 4) Create holder key and proof JWT
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
        proof_payload = {
            "iss": "demo-holder",
            "aud": ISSUER,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "nonce": c_nonce
        }
        proof_jwt = jwt.encode(proof_payload, holder_priv, algorithm=ALG_JOSE, headers=proof_header)

        # 5) Call credential (internally)
        device_cose_key = jwk_to_cose_ec2_map(holder_jwk)
        data = {"org.iso.18013.5.1": {"given_name": "Erika", "family_name": "Mustermann", "birth_date": "1990-01-01"}}
        cred_b64 = b64url(build_mdoc_issuersigned("org.iso.18013.5.1.mDL", data, device_cose_key))

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
            <h3>📝 Fill in Your Details</h3>
            <p>Please provide your personal information to issue your mdoc credential:</p>
        </div>

        <div class="step">
            <form method="POST">
                <div class="form-row">
                    <div class="form-group">
                        <label for="given_name">Given Name *</label>
                        <input type="text" id="given_name" name="given_name" value="{{ form_data.given_name or '' }}" required>
                    </div>
                    <div class="form-group">
                        <label for="family_name">Family Name *</label>
                        <input type="text" id="family_name" name="family_name" value="{{ form_data.family_name or '' }}" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="birth_date">Date of Birth *</label>
                    <input type="date" id="birth_date" name="birth_date" value="{{ form_data.birth_date or '' }}" required>
                </div>
                
                <div class="form-group">
                    <label for="document_number">Document Number</label>
                    <input type="text" id="document_number" name="document_number" value="{{ form_data.document_number or '' }}" placeholder="e.g., D1234567">
                </div>
                
                <div class="form-group">
                    <label for="issuing_jurisdiction">Issuing Jurisdiction</label>
                    <input type="text" id="issuing_jurisdiction" name="issuing_jurisdiction" value="{{ form_data.issuing_jurisdiction or '' }}" placeholder="e.g., DE">
                </div>
                
                <div class="form-group">
                    <label for="issuing_authority">Issuing Authority</label>
                    <input type="text" id="issuing_authority" name="issuing_authority" value="{{ form_data.issuing_authority or '' }}" placeholder="e.g., Bundesministerium des Innern">
                </div>
                
                <div class="form-group">
                    <label for="un_distinguishing_sign">UN Distinguishing Sign</label>
                    <input type="text" id="un_distinguishing_sign" name="un_distinguishing_sign" value="{{ form_data.un_distinguishing_sign or '' }}" placeholder="e.g., D">
                </div>
                
                <div class="form-group">
                    <label for="administrative_number">Administrative Number</label>
                    <input type="text" id="administrative_number" name="administrative_number" value="{{ form_data.administrative_number or '' }}" placeholder="e.g., 123456789">
                </div>
                
                <div class="form-group">
                    <label for="date_of_issue">Date of Issue</label>
                    <input type="date" id="date_of_issue" name="date_of_issue" value="{{ form_data.date_of_issue or '' }}">
                </div>
                
                <button type="submit">Request Credential</button>
            </form>
        </div>
        {% else %}
        
        <div class="step success">
            <h3>✅ Credential Issued Successfully!</h3>
            <p>The mdoc credential has been generated successfully using the ISO 18013-5 compliant format.</p>
        </div>

        <div class="step">
            <h3>👤 Personal Information Used</h3>
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
            <p>Copy this to test in the <a href="/verify" target="_blank">verification page</a> or <a href="https://paradym.id/tools/mdoc" target="_blank">Paradym mDOC debugger</a>:</p>
            <pre class="credential-display">{{ result.mdoc_b64url }}</pre>
        </div>

        <div class="step">
            <h3>🔍 Verification Result</h3>
            <pre>{{ result.verification | tojson(indent=2) }}</pre>
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
        # Provide default form data for GET requests
        default_form_data = {
            "given_name": "",
            "family_name": "",
            "birth_date": "",
            "document_number": "",
            "issuing_jurisdiction": "",
            "issuing_authority": "",
            "un_distinguishing_sign": "",
            "administrative_number": "",
            "date_of_issue": ""
        }
        return render_template_string(FORM_CREDENTIAL_HTML, form_data=default_form_data)
    
    # Get form data
    form_data = {
        "given_name": request.form.get("given_name", ""),
        "family_name": request.form.get("family_name", ""),
        "birth_date": request.form.get("birth_date", ""),
        "document_number": request.form.get("document_number", ""),
        "issuing_jurisdiction": request.form.get("issuing_jurisdiction", ""),
        "issuing_authority": request.form.get("issuing_authority", ""),
        "un_distinguishing_sign": request.form.get("un_distinguishing_sign", ""),
        "administrative_number": request.form.get("administrative_number", ""),
        "date_of_issue": request.form.get("date_of_issue", "")
    }
    
    # Validate required fields
    if not form_data["given_name"] or not form_data["family_name"] or not form_data["birth_date"]:
        return render_template_string(FORM_CREDENTIAL_HTML, form_data=form_data, result={"error": "Please fill in all required fields (Given Name, Family Name, and Date of Birth)"})
    
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
                "given_name": form_data["given_name"],
                "family_name": form_data["family_name"],
                "birth_date": form_data["birth_date"]
            }
        }
        
        # Add optional fields if provided
        if form_data["document_number"]:
            data["org.iso.18013.5.1"]["document_number"] = form_data["document_number"]
        if form_data["issuing_jurisdiction"]:
            data["org.iso.18013.5.1"]["issuing_jurisdiction"] = form_data["issuing_jurisdiction"]
        if form_data["issuing_authority"]:
            data["org.iso.18013.5.1"]["issuing_authority"] = form_data["issuing_authority"]
        if form_data["un_distinguishing_sign"]:
            data["org.iso.18013.5.1"]["un_distinguishing_sign"] = form_data["un_distinguishing_sign"]
        if form_data["administrative_number"]:
            data["org.iso.18013.5.1"]["administrative_number"] = form_data["administrative_number"]
        if form_data["date_of_issue"]:
            data["org.iso.18013.5.1"]["date_of_issue"] = form_data["date_of_issue"]
        
        # 5. Generate mdoc credential
        device_cose_key = jwk_to_cose_ec2_map(holder_jwk)
        mdoc_b64url = b64url(build_mdoc_issuersigned("org.iso.18013.5.1.mDL", data, device_cose_key))
        
        # 6. Test verification
        try:
            raw = b64url_decode_to_bytes(mdoc_b64url)
            issuer_signed = cbor2.loads(raw)
            
            # Verify signature
            issuer_auth = issuer_signed["issuerAuth"]
            sign1 = Sign1Message.decode(issuer_auth)
            mso = cbor2.loads(sign1.payload)
            sign1.key = _ISSUER_VERIFY_KEY
            sig_ok = sign1.verify_signature()
            
            # Verify digests
            ns_map = issuer_signed["nameSpaces"]
            vd = mso["valueDigests"]["nameSpaces"]
            dig_ok = True
            for ns, items in ns_map.items():
                for b in items:
                    item = cbor2.loads(b)
                    want = vd[ns][item["digestID"]]
                    got = hashlib.sha256(b).digest()
                    if want != got:
                        dig_ok = False
                        break
                if not dig_ok:
                    break
            
            verification = {
                "docType": mso.get("docType"),
                "validityInfo": mso.get("validityInfo"),
                "signature_valid": bool(sig_ok),
                "digests_valid": bool(dig_ok),
                "namespaces": {ns: [cbor2.loads(b)["elementIdentifier"] for b in items] for ns, items in ns_map.items()}
            }
            
        except Exception as e:
            verification = {"error": str(e)}
        
        result = {
            "personal_info": form_data,
            "jwk": holder_jwk,
            "nonce": nonce,
            "proof_jwt": proof_jwt,
            "mdoc_b64url": mdoc_b64url,
            "verification": verification
        }
        
        return render_template_string(FORM_CREDENTIAL_HTML, result=result)
        
    except Exception as e:
        return render_template_string(FORM_CREDENTIAL_HTML, form_data=form_data, result={"error": str(e)})

# ---------------------------------------------------------------------
if __name__ == "__main__":
    # For demo only (no TLS). In production, serve behind HTTPS and real hostname.
    app.run(host="0.0.0.0", port=5000, debug=True)
