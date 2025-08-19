# OIDC Backend API Documentation

This document describes the API endpoints available in the OIDC backend, including the new credential issuance and verification APIs.

## Base URL
```
http://localhost:5000
```

## Authentication
Most endpoints do not require authentication for demo purposes. In production, implement proper authentication mechanisms.

## API Endpoints

### 1. Issue Credential API

**Endpoint:** `POST /api/issue_credential`

**Description:** Issues a new credential and saves it to the database. This endpoint is designed for use with Angular frontend applications.

**Request Body:**
```json
{
  "credential_id": "string (required)",
  "subject_id": "string (required)",
  "type": "string (required) - Account|Custom|Membership|Identity",
  "format": "string (optional) - defaults to 'ISO mdoc'",
  "status": "string (optional) - defaults to 'active'",
  "given_name": "string (optional) - defaults to 'John'",
  "family_name": "string (optional) - defaults to 'Doe'",
  "birth_date": "string (optional) - defaults to '1990-01-01'",
  "custom_fields": {
    "field_name": "field_value"
  },
  "expires": "string (optional) - ISO format (YYYY-MM-DDTHH:MM:SS)"
}
```

**Example Request:**
```json
{
  "credential_id": "ACC-123456-ABC789",
  "subject_id": "did:example:123",
  "type": "Account",
  "given_name": "Jane",
  "family_name": "Smith",
  "birth_date": "1985-05-15",
  "custom_fields": {
    "account_number": "1234567890",
    "bank_name": "Example Bank"
  },
  "expires": "2025-12-31T23:59:59"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "credential": {
    "id": 1,
    "credential_id": "ACC-123456-ABC789",
    "subject_id": "did:example:123",
    "type": "Account",
    "format": "ISO mdoc",
    "status": "active",
    "issued": "2024-12-21T10:30:00",
    "expires": "2025-12-31T23:59:59"
  },
  "mdoc": {
    "base64url": "base64_encoded_credential_data",
    "hex": "hex_encoded_credential_data"
  },
  "jwk": {
    "kty": "EC",
    "crv": "P-256",
    "x": "base64_encoded_x_coordinate",
    "y": "base64_encoded_y_coordinate",
    "kid": "holder-ACC-123456-ABC789"
  },
  "proof_jwt": "jwt_proof_token",
  "nonce": "random_nonce_string"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Missing required field: credential_id"
}
```

### 2. Verify Credential API

**Endpoint:** `POST /api/verify_credential`

**Description:** Verifies a credential and saves the verification log to the database.

**Request Body:**
```json
{
  "credential": "string (required) - base64url encoded credential",
  "verifier": "string (optional) - defaults to 'API-Verifier'"
}
```

**Example Request:**
```json
{
  "credential": "base64url_encoded_credential_data",
  "verifier": "Angular-Frontend"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "verification": {
    "result": "PASS",
    "response_time_ms": 150,
    "verifier": "Angular-Frontend",
    "signature_valid": true,
    "digests_valid": true,
    "docType": "org.iso.18013.5.1.mDL",
    "validityInfo": {
      "issuanceDate": "2024-12-21",
      "expiryDate": "2025-12-21"
    },
    "namespaces": {
      "org.iso.18013.5.1": ["given_name", "family_name", "birth_date"]
    }
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Verification failed: Invalid credential format",
  "verification": {
    "result": "FAIL",
    "response_time_ms": 45,
    "verifier": "Angular-Frontend"
  }
}
```

### 3. Get Credentials API

**Endpoint:** `GET /api/credentials`

**Description:** Retrieves all credentials from the database.

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "credential_id": "ACC-123456-ABC789",
      "subject_id": "did:example:123",
      "type": "Account",
      "format": "ISO mdoc",
      "status": "active",
      "issued": "2024-12-21T10:30:00",
      "expires": "2025-12-31T23:59:59"
    }
  ],
  "count": 1
}
```

### 4. Get Verification Logs API

**Endpoint:** `GET /api/verification-logs`

**Description:** Retrieves all verification logs from the database.

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "checked_at": "2024-12-21T10:35:00",
      "credential_id": "ACC-123456-ABC789",
      "result": "PASS",
      "response_time": 150,
      "verifier": "Angular-Frontend"
    }
  ],
  "count": 1
}
```

### 5. Get Credential by ID API

**Endpoint:** `GET /api/credentials/{credential_id}`

**Description:** Retrieves a specific credential by its ID.

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "credential_id": "ACC-123456-ABC789",
    "subject_id": "did:example:123",
    "type": "Account",
    "format": "ISO mdoc",
    "status": "active",
    "issued": "2024-12-21T10:30:00",
    "expires": "2025-12-31T23:59:59"
  }
}
```

### 6. Get Verification Logs for Credential API

**Endpoint:** `GET /api/credentials/{credential_id}/verification-logs`

**Description:** Retrieves verification logs for a specific credential.

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "checked_at": "2024-12-21T10:35:00",
      "credential_id": "ACC-123456-ABC789",
      "result": "PASS",
      "response_time": 150,
      "verifier": "Angular-Frontend"
    }
  ],
  "count": 1
}
```

## Angular Frontend Integration

### Example Angular Service

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class CredentialService {
  private baseUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) { }

  issueCredential(credentialData: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/issue_credential`, credentialData);
  }

  verifyCredential(credential: string, verifier: string = 'Angular-Frontend'): Observable<any> {
    return this.http.post(`${this.baseUrl}/verify_credential`, {
      credential,
      verifier
    });
  }

  getCredentials(): Observable<any> {
    return this.http.get(`${this.baseUrl}/credentials`);
  }

  getVerificationLogs(): Observable<any> {
    return this.http.get(`${this.baseUrl}/verification-logs`);
  }
}
```

### Example Angular Component

```typescript
import { Component } from '@angular/core';
import { CredentialService } from './credential.service';

@Component({
  selector: 'app-credential',
  template: `
    <div>
      <h2>Issue Credential</h2>
      <form (ngSubmit)="issueCredential()">
        <input [(ngModel)]="credentialData.credential_id" placeholder="Credential ID" required>
        <input [(ngModel)]="credentialData.subject_id" placeholder="Subject ID" required>
        <select [(ngModel)]="credentialData.type" required>
          <option value="Account">Account</option>
          <option value="Identity">Identity</option>
          <option value="Membership">Membership</option>
        </select>
        <button type="submit">Issue Credential</button>
      </form>

      <h2>Verify Credential</h2>
      <textarea [(ngModel)]="credentialToVerify" placeholder="Paste credential data"></textarea>
      <button (click)="verifyCredential()">Verify</button>

      <div *ngIf="verificationResult">
        <h3>Verification Result</h3>
        <pre>{{ verificationResult | json }}</pre>
      </div>
    </div>
  `
})
export class CredentialComponent {
  credentialData = {
    credential_id: '',
    subject_id: '',
    type: 'Account'
  };
  credentialToVerify = '';
  verificationResult: any;

  constructor(private credentialService: CredentialService) { }

  issueCredential() {
    this.credentialService.issueCredential(this.credentialData)
      .subscribe({
        next: (response) => {
          console.log('Credential issued:', response);
          this.credentialToVerify = response.mdoc.base64url;
        },
        error: (error) => console.error('Error issuing credential:', error)
      });
  }

  verifyCredential() {
    this.credentialService.verifyCredential(this.credentialToVerify)
      .subscribe({
        next: (response) => {
          this.verificationResult = response;
          console.log('Verification result:', response);
        },
        error: (error) => console.error('Error verifying credential:', error)
      });
  }
}
```

## Error Handling

All API endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error description"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created (for credential issuance)
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `500` - Internal Server Error

## Testing

Use the provided test script to verify API functionality:

```bash
python test_new_apis.py
```

This script will:
1. Issue a test credential
2. Verify the issued credential
3. Query the database for credentials and verification logs
4. Display the results

## Database Integration

Both APIs automatically save data to the PostgreSQL database:

- **Issue Credential API**: Saves credential details to the `credential` table
- **Verify Credential API**: Saves verification attempts to the `verification_log` table

The database dashboard at `http://localhost:5000/dashboard` provides a web interface to view all stored data.

## Security Considerations

For production use, consider implementing:

1. **Authentication**: JWT tokens, API keys, or OAuth2
2. **Authorization**: Role-based access control
3. **Input Validation**: Comprehensive validation of all inputs
4. **Rate Limiting**: Prevent abuse of APIs
5. **HTTPS**: Secure communication
6. **Audit Logging**: Track all API usage
7. **Data Encryption**: Encrypt sensitive data at rest 