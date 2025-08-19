python -m venv .venv && source .venv/bin/activate
pip install flask cbor2 pycose cryptography pymdoccbor



Production considerations (must-haves)
Key management — Move signing keys to an HSM or cloud KMS. Publish the corresponding public key/certificate or configure DID resolution so wallets/verifiers can validate the signature. Never ship private scalar in code. collateral-library-production.s3.amazonaws.com
Issuer metadata / trust — You will need a trustworthy mechanism for verifiers (and wallets) to obtain the issuer’s verification key and possibly an authorization model for readers. The ISO spec and ecosystem docs describe trusted distribution / reader auth. ISORegulations.gov
Conformant claim names & test vectors — Use an existing library (e.g., pyMDOC-CBOR) or reference implementations (pagopa / openwallet examples) to ensure byte-level compatibility with wallets. Developer tooling will validate CBOR structure and COSE signature details. GitHub+1
Issuance protocol — Wire this issuer into an OIDC4VCI (OpenID for VC Issuance) or similar flow rather than an open endpoint. This binds the issuance to an authenticated user/session and prevents unauthorized issuance. OpenID Foundationauthlete.com
Presentation & privacy — Real wallets use session keys and selective disclosure patterns for privacy (Android Identity, Google Wallet). If you want direct wallet integration or online verifier flows, review those platform docs. Android Developers BlogGoogle for Developers

curl -s -X POST http://localhost:5000/issue-mdoc-iso \
  -H "Content-Type: application/json" \
  -d '{
    "givenName":"Jane",
    "familyName":"Doe",
    "dateOfBirth":"1990-01-01",
    "documentNumber":"D1234567",
    "issuing_jurisdiction":"US-CA",
    "domestic_driving_privileges":{"category":"C"},
    "issuer":"did:example:issuer-12345"
  }' | jq -r .mdoc_base64 > mdoc.b64

# decode to bytes (for inspection)
base64 -d mdoc.b64 > mdoc.cose
file mdoc.cose   # will be binary COSE_Sign1



https://github.com/IdentityPython/pyMDOC-CBOR?utm_source=chatgpt.com

https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html?utm_source=chatgpt.com

https://android-developers.googleblog.com/2020/11/privacy-preserving-features-in-mobile.html?utm_source=chatgpt.com

https://developers.google.com/wallet/identity/verify/accepting-ids-from-wallet-online?utm_source=chatgpt.com

https://openid.github.io/OpenID4VCI/openid-4-verifiable-credential-issuance-wg-draft.html#name-pre-authorized-code-flow
