import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { delay, map, catchError } from 'rxjs/operators';
import {
  Credential,
  CredentialMetrics,
  ActivityEntry,
  VerificationLog,
  AuditEntry,
  SystemHealth,
  IssueCredentialForm
} from '../models/credential.types';
import { environment } from '../../environments/environment';

// Backend API response interfaces
interface BackendCredentialResponse {
  success: boolean;
  credential: {
    id: number;
    credential_id: string;
    subject_id: string;
    type: string;
    format: string;
    status: string;
    issued: string;
    expires: string | null;
  };
  mdoc: {
    base64url: string;
    hex: string;
  };
  jwk: any;
  proof_jwt: string;
  nonce: string;
}

interface BackendCredentialsResponse {
  success: boolean;
  count: number;
  data: Array<{
    id: number;
    credential_id: string;
    subject_id: string;
    type: string;
    format: string;
    status: string;
    issued: string;
    expires: string | null;
  }>;
}

interface BackendVerificationLogsResponse {
  success: boolean;
  count: number;
  data: Array<{
    id: number;
    checked_at: string;
    credential_id: string;
    result: string;
    response_time: number;
    verifier: string;
  }>;
}

interface BackendRevokeResponse {
  success: boolean;
  message: string;
  credential: {
    id: number;
    credential_id: string;
    subject_id: string;
    type: string;
    format: string;
    status: string;
    issued: string;
    expires: string | null;
  };
  revocation_info: {
    revoked_at: string;
    reason: string;
  };
}

interface BackendMetricsResponse {
  success: boolean;
  data: {
    activeCredentials: number;
    newCredentials: number;
    totalVerifications: number;
    passRate: number;
    failRate: number;
    avgResponseTime: number;
    passRateChange: string;
    failRateChange: string;
    avgResponseTimeChange: string;
  };
}

interface BackendExtendResponse {
  success: boolean;
  message: string;
  credential: {
    id: number;
    credential_id: string;
    subject_id: string;
    type: string;
    format: string;
    status: string;
    issued: string;
    expires: string | null;
  };
  extension_info: {
    old_expiry_date: string | null;
    new_expiry_date: string;
    extended_at: string;
    reason: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class CredentialService {

  private apiUrl = environment.apiUrl;
  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
    })
  };

  // Fallback mock data for when backend is not available
  private mockCredentials: Credential[] = [
    {
      id: 'ACC-418277-QLK0',
      subjectId: 'did:xyz:fig23',
      type: 'Account',
      format: 'ISO mdoc',
      status: 'revoked',
      issuedAt: 'Aug 17, 2025',
      expiresAt: 'Never',
      claims: {
        'accountType': 'Premium',
        'verificationLevel': 'Level 2',
        'issuer': 'STREAM Platform'
      }
    }
  ];

  private mockMetrics: CredentialMetrics = {
    activeCredentials: 26,
    newCredentials: 39,
    totalVerifications: 852,
    passRate: 96.4,
    failRate: 3.6,
    avgResponseTime: 214,
    passRateChange: '+8.2%',
    failRateChange: '-1.3%',
    avgResponseTimeChange: '-23ms'
  };

  private mockActivity: ActivityEntry[] = [
    {
      id: '1',
      action: 'Credential Issue',
      details: 'Issued Account credential (iso_mdoc)',
      credentialId: 'ACC-418277-QLK0',
      user: 'System Admin',
      timestamp: 'Aug 17, 2025 04:37'
    }
  ];

  private mockVerificationLogs: VerificationLog[] = [
    {
      id: '1',
      checkedAt: 'Dec 21, 2024 05:39',
      credentialId: 'EMP-240008-H5R8',
      result: 'PASS',
      responseTime: 167,
      verifier: 'Web-Portal-002'
    }
  ];

  private mockSystemHealth: SystemHealth = {
    apiUptime: 99.99,
    systemStatus: 'Healthy',
    avgResponse: 89,
    activeSessions: 23,
    uptimeChange: '+0.01%',
    avgResponseChange: '-12ms',
    activeSessionsChange: '+4.5%'
  };

  constructor(private http: HttpClient) {}

  getMetrics(): Observable<CredentialMetrics> {
    return this.http.get<BackendMetricsResponse>(`${this.apiUrl}/api/metrics`, this.httpOptions)
      .pipe(
        map(response => {
          if (response.success) {
            return {
              activeCredentials: response.data.activeCredentials,
              newCredentials: response.data.newCredentials,
              totalVerifications: response.data.totalVerifications,
              passRate: response.data.passRate,
              failRate: response.data.failRate,
              avgResponseTime: response.data.avgResponseTime,
              passRateChange: response.data.passRateChange,
              failRateChange: response.data.failRateChange,
              avgResponseTimeChange: response.data.avgResponseTimeChange
            };
          }
          return this.mockMetrics; // Fallback to mock if backend fails
        }),
        catchError(error => {
          console.warn('Backend API not available, using mock data:', error);
          return of(this.mockMetrics);
        })
      );
  }

  getCredentials(): Observable<Credential[]> {
    return this.http.get<BackendCredentialsResponse>(`${this.apiUrl}/api/credentials`, this.httpOptions)
      .pipe(
        map(response => {
          if (response.success) {
            return response.data.map(cred => this.mapBackendCredentialToFrontend(cred));
          }
          return [];
        }),
        catchError(error => {
          console.warn('Backend API not available, using mock data:', error);
          return of(this.mockCredentials);
        })
      );
  }

  getRecentActivity(): Observable<ActivityEntry[]> {
    return of(this.mockActivity);
  }

  getVerificationLogs(): Observable<VerificationLog[]> {
    return this.http.get<BackendVerificationLogsResponse>(`${this.apiUrl}/api/verification-logs`, this.httpOptions)
      .pipe(
        map(response => {
          if (response.success) {
            return response.data.map(log => this.mapBackendVerificationLogToFrontend(log));
          }
          return [];
        }),
        catchError(error => {
          console.warn('Backend API not available, using mock data:', error);
          return of(this.mockVerificationLogs);
        })
      );
  }

  getSystemHealth(): Observable<SystemHealth> {
    return of(this.mockSystemHealth);
  }

  getCredentialById(id: string): Observable<Credential | undefined> {
    return this.getCredentials().pipe(
      map(credentials => credentials.find(cred => cred.id === id))
    );
  }

  /**
   * Get full credential details including claims
   */
  getCredentialDetails(credentialId: string): Observable<Credential> {
    return this.getCredentialById(credentialId).pipe(
      map(credential => {
        if (!credential) {
          throw new Error('Credential not found');
        }
        return credential;
      })
    );
  }

  /**
   * Issue a new credential - API call to /api/issue_credential
   */
  issueCredential(credentialData: IssueCredentialForm): Observable<{ success: boolean; message: string; credentialId: string; credential: Credential; mdoc: { base64url: string; hex: string }; jwk: any; proof_jwt: string }> {
    // Validate required fields
    if (!credentialData.type || !credentialData.format || !credentialData.subjectId) {
      return throwError(() => new Error('Missing required fields: type, format, or subjectId'));
    }

    // Generate unique credential ID
    const credentialId = this.generateCredentialId(credentialData.type);

    // Prepare data for backend API
    const backendData = {
      credential_id: credentialId,
      type: credentialData.type,
      subject_id: credentialData.subjectId,
      format: credentialData.format,
      status: 'active',
      expires: credentialData.expirationDate || null,
      given_name: this.extractClaimValue(credentialData.claims, 'given_name') || 'John',
      family_name: this.extractClaimValue(credentialData.claims, 'family_name') || 'Doe',
      birth_date: this.extractClaimValue(credentialData.claims, 'birth_date') || '1990-01-01',
      custom_fields: this.convertClaimsArrayToObject(credentialData.claims),
      account_id: credentialData.accountId
    };

    // Call backend API
    return this.http.post<BackendCredentialResponse>(`${this.apiUrl}/api/issue_credential`, backendData, this.httpOptions)
      .pipe(
        map(response => {
          console.log('Backend response:', response);
          if (response.success) {
            const newCredential = this.mapBackendCredentialToFrontend(response.credential);
            
            // Add to local mock data for immediate UI update
            this.mockCredentials.unshift(newCredential);
            this.mockMetrics.activeCredentials++;
            this.mockMetrics.newCredentials++;

            // Add to activity log
            this.mockActivity.unshift({
              id: Date.now().toString(),
              action: 'Credential Issue',
              details: `Issued ${credentialData.type} credential (${credentialData.format.toLowerCase().replace(' ', '_')})`,
              credentialId: credentialId,
              user: 'System Admin',
              timestamp: new Date().toLocaleString()
            });

            return {
              success: true,
              message: 'Credential issued successfully',
              credentialId: credentialId,
              credential: newCredential,
              mdoc: response.mdoc,
              jwk: response.jwk,
              proof_jwt: response.proof_jwt
            };
          } else {
            throw new Error('Failed to issue credential');
          }
        }),
        catchError(error => {
          console.error('Error issuing credential:', error);
          return throwError(() => new Error(error.error?.error || 'Failed to issue credential'));
        })
      );
  }

  /**
   * Revoke a credential
   */
  revokeCredential(credentialId: string): Observable<{ success: boolean; message: string }> {
    // Call backend API
    return this.http.post<BackendRevokeResponse>(`${this.apiUrl}/api/revoke`, {
      credential_id: credentialId,
      reason: "Revoked by user request"
    }, this.httpOptions)
      .pipe(
        map(response => {
          if (response.success) {
            // Update local mock data for immediate UI update
            const credentialIndex = this.mockCredentials.findIndex(cred => cred.id === credentialId);
            if (credentialIndex !== -1) {
              this.mockCredentials[credentialIndex].status = "revoked";
            }

            // Add to activity log
            this.mockActivity.unshift({
              id: Date.now().toString(),
              action: "Credential Revoke",
              details: `Revoked credential ${credentialId}`,
              credentialId: credentialId,
              user: "System Admin",
              timestamp: new Date().toLocaleString()
            });

            return {
              success: true,
              message: response.message
            };
          } else {
            throw new Error(response.message || "Failed to revoke credential");
          }
        }),
        catchError(error => {
          console.error("Error revoking credential:", error);
          return throwError(() => new Error(error.error?.error || "Failed to revoke credential"));
        })
      );
  }

  /**
   * Extend credential expiry date
   */
  extendCredentialExpiry(credentialId: string, newExpiryDate: string): Observable<{ success: boolean; message: string }> {
    // Call backend API directly - no need to check local mock data first
    const backendData = {
      credential_id: credentialId,
      new_expiry_date: newExpiryDate
    };

    // Call backend API
    return this.http.post<BackendExtendResponse>(`${this.apiUrl}/api/extend_expiry_date`, backendData, this.httpOptions)
      .pipe(
        map(response => {
          if (response.success) {
            // Update local mock data for immediate UI update
            const credentialIndex = this.mockCredentials.findIndex(cred => cred.id === credentialId);
            if (credentialIndex !== -1) {
              this.mockCredentials[credentialIndex].expiresAt = new Date(response.extension_info.new_expiry_date).toLocaleDateString();
              if (this.mockCredentials[credentialIndex].status === 'expired') {
                this.mockCredentials[credentialIndex].status = 'active';
              }
            }

            // Add to activity log
            this.mockActivity.unshift({
              id: Date.now().toString(),
              action: 'Credential Extend',
              details: `Extended credential expiry to ${new Date(response.extension_info.new_expiry_date).toLocaleDateString()}`,
              credentialId: credentialId,
              user: 'System Admin',
              timestamp: new Date().toLocaleString()
            });

            return {
              success: true,
              message: response.message
            };
          } else {
            throw new Error(response.message || "Failed to extend credential expiry");
          }
        }),
        catchError(error => {
          console.error("Error extending credential expiry:", error);
          return throwError(() => new Error(error.error?.error || "Failed to extend credential expiry"));
        })
      );
  }

  // Helper methods
  private generateCredentialId(type: string): string {
    const prefix = type.substring(0, 3).toUpperCase();
    const timestamp = Date.now().toString().slice(-6);
    const random = Math.random().toString(36).substring(2, 6).toUpperCase();
    return `${prefix}-${timestamp}-${random}`;
  }

  private convertClaimsArrayToObject(claims: Array<{ key: string; value: string }>): Record<string, any> {
    const claimsObject: Record<string, any> = {};
    claims.forEach(claim => {
      if (claim.key && claim.value) {
        claimsObject[claim.key] = claim.value;
      }
    });
    return claimsObject;
  }

  private extractClaimValue(claims: Array<{ key: string; value: string }>, key: string): string | null {
    const claim = claims.find(c => c.key === key);
    return claim ? claim.value : null;
  }

  private mapBackendCredentialToFrontend(backendCred: any): Credential {
    return {
      id: backendCred.credential_id,
      subjectId: backendCred.subject_id,
      type: backendCred.type as any,
      format: backendCred.format as any,
      status: backendCred.status as any,
      issuedAt: new Date(backendCred.issued).toLocaleDateString(),
      expiresAt: backendCred.expires ? new Date(backendCred.expires).toLocaleDateString() : 'Never',
      claims: {}
    };
  }

  private mapBackendVerificationLogToFrontend(backendLog: any): VerificationLog {
    return {
      id: backendLog.id.toString(),
      checkedAt: new Date(backendLog.checked_at).toLocaleString(),
      credentialId: backendLog.credential_id,
      result: backendLog.result as any,
      responseTime: backendLog.response_time,
      verifier: backendLog.verifier
    };
  }
}
