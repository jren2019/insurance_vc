import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { Credential } from '../../models/credential.types';

@Component({
  selector: 'app-credential-details-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatDividerModule
  ],
  template: `
    <div class="credential-details-dialog">
      <div mat-dialog-title class="dialog-header">
        <div class="header-content">
          <mat-icon class="credential-icon">account_box</mat-icon>
          <div>
            <h2>Credential Details</h2>
            <p class="credential-id">{{ data.id }}</p>
          </div>
        </div>
        <button mat-icon-button (click)="close()" class="close-btn">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <div mat-dialog-content class="dialog-content">
        <div class="credential-info">
          <!-- Basic Information -->
          <div class="info-section">
            <h3>Basic Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <label>Credential ID:</label>
                <span class="credential-link">{{ data.id }}</span>
              </div>
              <div class="info-item">
                <label>Subject ID:</label>
                <span>{{ data.subjectId }}</span>
              </div>
              <div class="info-item">
                <label>Type:</label>
                <span>{{ data.type }}</span>
              </div>
              <div class="info-item">
                <label>Format:</label>
                <span>{{ data.format }}</span>
              </div>
              <div class="info-item">
                <label>Status:</label>
                <mat-chip [class]="'status-' + data.status" class="status-chip">
                  {{ data.status | titlecase }}
                </mat-chip>
              </div>
              <div class="info-item">
                <label>Issued At:</label>
                <span>{{ data.issuedAt }}</span>
              </div>
              <div class="info-item">
                <label>Expires At:</label>
                <span>{{ data.expiresAt || 'Never' }}</span>
              </div>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- Claims -->
          <div class="info-section" *ngIf="data.claims">
            <h3>Claims</h3>
            <div class="claims-container">
              <div *ngFor="let claim of getClaimsArray()" class="claim-item">
                <div class="claim-key">{{ claim.key }}</div>
                <div class="claim-value">{{ claim.value }}</div>
              </div>

              <div *ngIf="getClaimsArray().length === 0" class="no-claims">
                <mat-icon>info</mat-icon>
                <span>No claims available for this credential</span>
              </div>
            </div>
          </div>

          <mat-divider></mat-divider>

          <!-- JSON View -->
          <div class="info-section">
            <h3>JSON Representation</h3>
            <div class="json-container">
              <pre class="json-content">{{ getCredentialJSON() }}</pre>
            </div>
          </div>
        </div>
      </div>

      <div mat-dialog-actions class="dialog-actions">
        <button mat-button (click)="close()" class="cancel-btn">Close</button>
        <button mat-raised-button color="primary" (click)="downloadJSON()" class="download-btn">
          <mat-icon>download</mat-icon>
          Download JSON
        </button>
      </div>
    </div>
  `,
  styles: [`
    .credential-details-dialog {
      width: 100%;
      max-width: 800px;
      font-family: 'Inter', sans-serif;
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 24px 0 24px;
      margin: 0;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .credential-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: #4A90E2;
    }

    .header-content h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: #2c3e50;
    }

    .credential-id {
      margin: 4px 0 0 0;
      font-size: 14px;
      color: #7f8c8d;
      font-family: 'Courier New', monospace;
    }

    .close-btn {
      color: #7f8c8d;
    }

    .dialog-content {
      padding: 24px;
      max-height: 70vh;
      overflow-y: auto;
    }

    .info-section {
      margin-bottom: 24px;
    }

    .info-section h3 {
      margin: 0 0 16px 0;
      font-size: 18px;
      font-weight: 600;
      color: #2c3e50;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 16px;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .info-item label {
      font-size: 12px;
      font-weight: 600;
      color: #7f8c8d;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .info-item span {
      font-size: 14px;
      color: #2c3e50;
      font-weight: 500;
    }

    .credential-link {
      color: #4A90E2 !important;
      font-family: 'Courier New', monospace;
    }

    .status-chip {
      align-self: flex-start;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
      padding: 4px 12px;
      text-transform: capitalize;
    }

    .status-chip.status-active {
      background-color: #d4edda;
      color: #155724;
    }

    .status-chip.status-revoked {
      background-color: #f8d7da;
      color: #721c24;
    }

    .status-chip.status-expired {
      background-color: #fff3cd;
      color: #856404;
    }

    .status-chip.status-pending {
      background-color: #cce5ff;
      color: #004085;
    }

    .claims-container {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 16px;
    }

    .claim-item {
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 16px;
      padding: 12px 0;
      border-bottom: 1px solid #e9ecef;
    }

    .claim-item:last-child {
      border-bottom: none;
    }

    .claim-key {
      font-size: 13px;
      font-weight: 600;
      color: #495057;
      font-family: 'Courier New', monospace;
    }

    .claim-value {
      font-size: 14px;
      color: #2c3e50;
      word-break: break-all;
    }

    .no-claims {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #7f8c8d;
      font-style: italic;
    }

    .json-container {
      background: #2c3e50;
      border-radius: 8px;
      padding: 16px;
      max-height: 300px;
      overflow: auto;
    }

    .json-content {
      color: #ecf0f1;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.5;
      margin: 0;
      white-space: pre-wrap;
    }

    .dialog-actions {
      padding: 0 24px 24px 24px;
      gap: 12px;
    }

    .cancel-btn {
      color: #7f8c8d;
    }

    .download-btn {
      background: #4A90E2;
      color: white;
    }

    mat-divider {
      margin: 24px 0;
    }
  `]
})
export class CredentialDetailsDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<CredentialDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: Credential
  ) {}

  close(): void {
    this.dialogRef.close();
  }

  getClaimsArray(): Array<{key: string, value: string}> {
    if (!this.data.claims) return [];

    return Object.entries(this.data.claims).map(([key, value]) => ({
      key,
      value: typeof value === 'string' ? value : JSON.stringify(value)
    }));
  }

  getCredentialJSON(): string {
    return JSON.stringify(this.data, null, 2);
  }

  downloadJSON(): void {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(this.getCredentialJSON());
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `credential-${this.data.id}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  }
}
