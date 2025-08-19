# Angular-Flask Integration Guide

## Overview
This guide explains how the Angular frontend integrates with the Flask backend for OIDC credential management.

## Backend API Endpoints

### 1. Issue Credential API
**Endpoint:** `POST /api/issue_credential`

**Request Body:**
```json
{
  "credential_id": "ACC-123456-ABC123",
  "type": "Account",
  "subject_id": "did:example:123",
  "format": "ISO mdoc",
  "given_name": "John",
  "family_name": "Doe",
  "birth_date": "1990-01-01",
  "custom_fields": {
    "nationality": "US",
    "document_number": "123456789"
  }
}
```

**Response:**
```json
{
  "success": true,
  "credential": {
    "id": 1,
    "credential_id": "ACC-123456-ABC123",
    "subject_id": "did:example:123",
    "type": "Account",
    "format": "ISO mdoc",
    "status": "active",
    "issued": "2024-08-18T15:30:00",
    "expires": null
  },
  "mdoc": {
    "base64url": "...",
    "hex": "..."
  },
  "jwk": {...},
  "proof_jwt": "...",
  "nonce": "..."
}
```

### 2. Get Credentials API
**Endpoint:** `GET /api/credentials`

**Response:**
```json
{
  "success": true,
  "count": 46,
  "data": [
    {
      "id": 1,
      "credential_id": "ACC-123456-ABC123",
      "subject_id": "did:example:123",
      "type": "Account",
      "format": "ISO mdoc",
      "status": "active",
      "issued": "2024-08-18T15:30:00",
      "expires": null
    }
  ]
}
```

### 3. Get Verification Logs API
**Endpoint:** `GET /api/verification-logs`

**Response:**
```json
{
  "success": true,
  "count": 147,
  "data": [
    {
      "id": 1,
      "checked_at": "2024-08-18T15:30:00",
      "credential_id": "ACC-123456-ABC123",
      "result": "PASS",
      "response_time": 150,
      "verifier": "Web-Portal-001"
    }
  ]
}
```

## Angular Service Integration

### Updated CredentialService
The `CredentialService` has been updated to:

1. **Use HttpClient** for API calls
2. **Map backend responses** to frontend models
3. **Handle errors gracefully** with fallback to mock data
4. **Generate unique credential IDs** for each request

### Key Features:
- **Real API Integration**: Calls actual Flask backend endpoints
- **Error Handling**: Falls back to mock data if backend is unavailable
- **Data Mapping**: Converts backend response format to frontend format
- **Unique IDs**: Generates unique credential IDs for each issuance

### Environment Configuration
```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000'
};
```

## Setup Instructions

### 1. Start Flask Backend
```bash
cd /home/superuser/projects/sush/oidc/oidc_backend
source venv/bin/activate
python app_with_db.py
```

### 2. Start Angular Frontend
```bash
cd /home/superuser/projects/sush/oidc/oidc_frontend
npm start
```

### 3. Test Integration
- Open http://localhost:4200 in your browser
- Navigate to the credential issuance form
- Fill out the form and submit
- Check the browser console for API calls
- Verify data appears in the credentials list

## CORS Configuration
The Flask backend includes CORS headers to allow requests from the Angular frontend.

## Error Handling
- If the backend is unavailable, the frontend falls back to mock data
- API errors are logged to the console
- User-friendly error messages are displayed

## Testing
Use the test-integration.html file to test API endpoints directly:
```bash
# Open in browser
open test-integration.html
```

## Next Steps
1. Add more API endpoints (revoke, extend, etc.)
2. Implement real-time updates
3. Add authentication and authorization
4. Implement error retry logic
5. Add loading states and better UX
