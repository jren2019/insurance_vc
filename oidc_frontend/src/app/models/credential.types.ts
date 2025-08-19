export interface Credential {
  id: string;
  subjectId: string;
  type: CredentialType;
  format: CredentialFormat;
  status: CredentialStatus;
  issuedAt: string;
  expiresAt?: string;
  claims?: Record<string, any>;
}

export interface CredentialMetrics {
  activeCredentials: number;
  newCredentials: number;
  totalVerifications: number;
  passRate: number;
  failRate: number;
  avgResponseTime: number;
  passRateChange: string;
  failRateChange: string;
  avgResponseTimeChange: string;
}

export interface ActivityEntry {
  id: string;
  action: ActivityAction;
  details: string;
  credentialId: string;
  user: string;
  timestamp: string;
}

export interface VerificationLog {
  id: string;
  checkedAt: string;
  credentialId: string;
  result: VerificationResult;
  responseTime: number;
  verifier: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  action: AuditAction;
  user: string;
  credentialId: string;
  details: string;
}

export interface SystemHealth {
  apiUptime: number;
  systemStatus: 'Healthy' | 'Warning' | 'Critical';
  avgResponse: number;
  activeSessions: number;
  uptimeChange: string;
  avgResponseChange: string;
  activeSessionsChange: string;
}

export interface IssueCredentialForm {
  type: CredentialType;
  format: CredentialFormat;
  subjectId: string;
  validFrom: string;
  expirationDate?: string;
  claims: Array<{ key: string; value: string }>;
  accountId: string;
}

export type CredentialType =
  | 'Account'
  | 'Custom'
  | 'Membership'
  | 'Identity'
  | 'Employment';

export type CredentialFormat = 'ISO mdoc' | 'W3C VC (JWT)';

export type CredentialStatus =
  | 'active'
  | 'revoked'
  | 'expired'
  | 'pending';

export type ActivityAction =
  | 'Credential Issue'
  | 'Credential Revoke'
  | 'Credential Extend';

export type VerificationResult = 'PASS' | 'FAIL';

export type AuditAction =
  | 'Credential Revoke'
  | 'Credential Issue'
  | 'Credential Extend';
