import { Component, OnInit, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialogModule, MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { ReactiveFormsModule, FormControl } from '@angular/forms';
import { CredentialService } from '../../services/credential.service';
import { Credential } from '../../models/credential.types';
import { CredentialDetailsDialogComponent } from './credential-details-dialog.component';

@Component({
  selector: 'app-manage-credentials',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatFormFieldModule,
    MatChipsModule,
    MatMenuModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatNativeDateModule,
    ReactiveFormsModule
  ],
  template: `
    <div class="manage-credentials">

      <mat-card class="credentials-table-card">
        <div class="table-header">
          <div class="search-filters">
            <mat-form-field appearance="outline" class="search-field">
              <mat-label>Search by credential or subject ID...</mat-label>
              <input matInput>
              <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>All Status</mat-label>
              <mat-select>
                <mat-option value="all">All Status</mat-option>
                <mat-option value="active">Active</mat-option>
                <mat-option value="revoked">Revoked</mat-option>
                <mat-option value="expired">Expired</mat-option>
                <mat-option value="pending">Pending</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>All Types</mat-label>
              <mat-select>
                <mat-option value="all">All Types</mat-option>
                <mat-option value="Account">Account</mat-option>
                <mat-option value="Custom">Custom</mat-option>
                <mat-option value="Membership">Membership</mat-option>
                <mat-option value="Identity">Identity</mat-option>
                <mat-option value="Employment">Employment</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>All Formats</mat-label>
              <mat-select>
                <mat-option value="all">All Formats</mat-option>
                <mat-option value="ISO mdoc">ISO mdoc</mat-option>
                <mat-option value="W3C VC (JWT)">W3C VC (JWT)</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="table-info">
            Showing {{ credentials.length }} of {{ credentials.length }} credentials
          </div>
        </div>

        <div class="table-container">
          <table mat-table [dataSource]="credentials" class="credentials-table">
            <ng-container matColumnDef="credentialId">
              <th mat-header-cell *matHeaderCellDef>Credential ID</th>
              <td mat-cell *matCellDef="let credential">
                <a href="#" class="credential-link" (click)="$event.preventDefault(); viewCredentialDetails(credential)">
                  {{ credential.id }}
                </a>
              </td>
            </ng-container>

            <ng-container matColumnDef="subjectId">
              <th mat-header-cell *matHeaderCellDef>Subject ID</th>
              <td mat-cell *matCellDef="let credential">{{ credential.subjectId }}</td>
            </ng-container>

            <ng-container matColumnDef="type">
              <th mat-header-cell *matHeaderCellDef>Type</th>
              <td mat-cell *matCellDef="let credential">{{ credential.type }}</td>
            </ng-container>

            <ng-container matColumnDef="format">
              <th mat-header-cell *matHeaderCellDef>Format</th>
              <td mat-cell *matCellDef="let credential">{{ credential.format }}</td>
            </ng-container>

            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let credential">
                <mat-chip [class]="'status-' + credential.status" class="status-chip">
                  {{ credential.status }}
                </mat-chip>
              </td>
            </ng-container>

            <ng-container matColumnDef="issued">
              <th mat-header-cell *matHeaderCellDef>Issued</th>
              <td mat-cell *matCellDef="let credential">{{ credential.issuedAt }}</td>
            </ng-container>

            <ng-container matColumnDef="expires">
              <th mat-header-cell *matHeaderCellDef>Expires</th>
              <td mat-cell *matCellDef="let credential">{{ credential.expiresAt || 'Never' }}</td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let credential">
                <button mat-icon-button [matMenuTriggerFor]="actionsMenu" class="actions-btn">
                  <mat-icon>more_vert</mat-icon>
                </button>
                <mat-menu #actionsMenu="matMenu">
                  <button mat-menu-item (click)="viewCredentialDetails(credential)">
                    <mat-icon>visibility</mat-icon>
                    <span>View Credential Details</span>
                  </button>
                  <button mat-menu-item
                          (click)="revokeCredential(credential)"
                          [disabled]="credential.status === 'revoked' || isLoading">
                    <mat-icon>block</mat-icon>
                    <span>Revoke Credential</span>
                  </button>
                  <button mat-menu-item
                          (click)="extendExpiryDate(credential)"
                          [disabled]="credential.status === 'revoked' || isLoading">
                    <mat-icon>schedule</mat-icon>
                    <span>Extend Expiry Date</span>
                  </button>
                </mat-menu>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"
                class="table-row"></tr>
          </table>
        </div>

        <!-- Loading Overlay -->
        <div *ngIf="isLoading" class="loading-overlay">
          <mat-spinner diameter="50"></mat-spinner>
          <p>{{ loadingMessage }}</p>
        </div>
      </mat-card>
    </div>

    <!-- Extend Expiry Date Dialog -->
    <div #extendDialog style="display: none;">
      <div class="extend-dialog-content">
        <h3>Extend Expiry Date</h3>
        <p>Select a new expiry date for credential: <strong>{{ selectedCredential?.id }}</strong></p>

        <mat-form-field appearance="outline" class="date-field">
          <mat-label>New Expiry Date</mat-label>
          <input matInput [matDatepicker]="picker" [formControl]="newExpiryDate" [min]="minDate">
          <mat-datepicker-toggle matIconSuffix [for]="picker"></mat-datepicker-toggle>
          <mat-datepicker #picker></mat-datepicker>
        </mat-form-field>

        <div class="dialog-actions">
          <button mat-button (click)="cancelExtendExpiry()">Cancel</button>
          <button mat-raised-button color="primary"
                  (click)="confirmExtendExpiry()"
                  [disabled]="!newExpiryDate.value || isLoading">
            <mat-icon *ngIf="isLoading; else extendIcon">
              <mat-spinner diameter="16"></mat-spinner>
            </mat-icon>
            <ng-template #extendIcon>
              <mat-icon>schedule</mat-icon>
            </ng-template>
            Extend Expiry
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .manage-credentials {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 32px;
    }

    .header-content h1 {
      font-size: 28px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0 0 8px 0;
    }

    .header-content p {
      color: #7f8c8d;
      margin: 0;
    }

    .issue-new-btn {
      height: 48px;
      border-radius: 8px;
      font-weight: 500;
      text-transform: none;
      background: #4A90E2;
      color: white;
    }

    .credentials-table-card {
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
      position: relative;
    }

    .table-header {
      padding: 24px;
      border-bottom: 1px solid #e0e0e0;
    }

    .search-filters {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    .search-field {
      flex: 2;
      min-width: 300px;
    }

    .filter-field {
      flex: 1;
      min-width: 150px;
    }

    .table-info {
      color: #7f8c8d;
      font-size: 14px;
    }

    .table-container {
      overflow-x: auto;
    }

    .credentials-table {
      width: 100%;
    }

    .credentials-table th {
      font-weight: 600;
      color: #34495e;
      border-bottom: 2px solid #ecf0f1;
      padding: 16px;
    }

    .credentials-table td {
      padding: 16px;
      border-bottom: 1px solid #ecf0f1;
    }

    .table-row {
      transition: background-color 0.2s;
    }

    .table-row:hover {
      background-color: #f8f9fa;
    }

    .credential-link {
      color: #4A90E2;
      text-decoration: none;
      font-weight: 500;
      cursor: pointer;
    }

    .credential-link:hover {
      text-decoration: underline;
    }

    .status-chip {
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

    .actions-btn {
      color: #7f8c8d;
    }

    .loading-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.8);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      z-index: 10;
    }

    .loading-overlay p {
      color: #7f8c8d;
      font-weight: 500;
    }

    .extend-dialog-content {
      padding: 24px;
      min-width: 400px;
    }

    .extend-dialog-content h3 {
      margin: 0 0 16px 0;
      color: #2c3e50;
    }

    .extend-dialog-content p {
      margin: 0 0 24px 0;
      color: #7f8c8d;
    }

    .date-field {
      width: 100%;
      margin-bottom: 24px;
    }

    .dialog-actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    }
  `]
})
export class ManageCredentialsComponent implements OnInit {
  credentials: Credential[] = [];
  displayedColumns = [
    'credentialId',
    'subjectId',
    'type',
    'format',
    'status',
    'issued',
    'expires',
    'actions'
  ];

  isLoading = false;
  loadingMessage = '';
  selectedCredential: Credential | null = null;
  newExpiryDate = new FormControl(new Date());
  minDate = new Date();

  constructor(
    private credentialService: CredentialService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadCredentials();
  }

  loadCredentials() {
    this.credentialService.getCredentials().subscribe(credentials => {
      // Sort credentials by issuedAt in descending order (latest first)
      this.credentials = credentials.sort((a, b) => {
        const dateA = new Date(a.issuedAt);
        const dateB = new Date(b.issuedAt);
        return dateB.getTime() - dateA.getTime();
      });
    });
  }

  /**
   * View credential details in a dialog
   */
  viewCredentialDetails(credential: Credential) {
    this.isLoading = true;
    this.loadingMessage = 'Loading credential details...';

    this.credentialService.getCredentialDetails(credential.id).subscribe({
      next: (fullCredential) => {
        this.isLoading = false;

        const dialogRef = this.dialog.open(CredentialDetailsDialogComponent, {
          width: '800px',
          maxWidth: '90vw',
          maxHeight: '90vh',
          data: fullCredential,
          panelClass: 'credential-details-dialog-panel'
        });

        dialogRef.afterClosed().subscribe(result => {
          console.log('Credential details dialog closed');
        });
      },
      error: (error) => {
        this.isLoading = false;
        this.showErrorMessage('Failed to load credential details: ' + error.message);
      }
    });
  }

  /**
   * Revoke a credential with confirmation
   */
  revokeCredential(credential: Credential) {
    if (credential.status === 'revoked') {
      this.showErrorMessage('Credential is already revoked');
      return;
    }

    // Show confirmation dialog
    const confirmDialog = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Revoke Credential',
        message: `Are you sure you want to revoke credential "${credential.id}"? This action cannot be undone.`,
        confirmText: 'Revoke',
        cancelText: 'Cancel',
        confirmColor: 'warn'
      }
    });

    confirmDialog.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.performRevokeCredential(credential);
      }
    });
  }

  private performRevokeCredential(credential: Credential) {
    this.isLoading = true;
    this.loadingMessage = 'Revoking credential...';

    this.credentialService.revokeCredential(credential.id).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.showSuccessMessage(response.message);
        this.loadCredentials(); // Refresh the table
      },
      error: (error) => {
        this.isLoading = false;
        this.showErrorMessage('Failed to revoke credential: ' + error.message);
      }
    });
  }

  /**
   * Extend credential expiry date
   */
  extendExpiryDate(credential: Credential) {
    if (credential.status === 'revoked') {
      this.showErrorMessage('Cannot extend revoked credential');
      return;
    }

    this.selectedCredential = credential;

    // Set default date to 1 year from now
    const defaultDate = new Date();
    defaultDate.setFullYear(defaultDate.getFullYear() + 1);
    this.newExpiryDate.setValue(defaultDate);

    // Show extend expiry dialog
    const extendDialog = this.dialog.open(ExtendExpiryDialogComponent, {
      width: '400px',
      data: {
        credential: credential,
        newExpiryDate: this.newExpiryDate
      }
    });

    extendDialog.afterClosed().subscribe(result => {
      if (result && result.newExpiryDate) {
        this.performExtendExpiry(credential, result.newExpiryDate);
      }
    });
  }

  private performExtendExpiry(credential: Credential, newExpiryDate: string) {
    this.isLoading = true;
    this.loadingMessage = 'Extending credential expiry...';

    this.credentialService.extendCredentialExpiry(credential.id, newExpiryDate).subscribe({
      next: (response) => {
        this.isLoading = false;
        this.showSuccessMessage(response.message);
        this.loadCredentials(); // Refresh the table
      },
      error: (error) => {
        this.isLoading = false;
        this.showErrorMessage('Failed to extend credential expiry: ' + error.message);
      }
    });
  }

  cancelExtendExpiry() {
    this.selectedCredential = null;
  }

  confirmExtendExpiry() {
    if (this.selectedCredential && this.newExpiryDate.value) {
      const formattedDate = this.newExpiryDate.value.toISOString();
      this.performExtendExpiry(this.selectedCredential, formattedDate);
    }
  }

  private showSuccessMessage(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['success-snackbar']
    });
  }

  private showErrorMessage(message: string) {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar']
    });
  }
}

// Confirmation Dialog Component
@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="confirm-dialog">
      <h2 mat-dialog-title>{{ data.title }}</h2>
      <div mat-dialog-content>
        <p>{{ data.message }}</p>
      </div>
      <div mat-dialog-actions class="dialog-actions">
        <button mat-button (click)="onCancel()">{{ data.cancelText }}</button>
        <button mat-raised-button [color]="data.confirmColor" (click)="onConfirm()">
          {{ data.confirmText }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog {
      font-family: 'Inter', sans-serif;
    }
    .dialog-actions {
      gap: 12px;
    }
  `]
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {}

  onCancel(): void {
    this.dialogRef.close(false);
  }

  onConfirm(): void {
    this.dialogRef.close(true);
  }
}

// Extend Expiry Dialog Component
@Component({
  selector: 'app-extend-expiry-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    ReactiveFormsModule
  ],
  template: `
    <div class="extend-expiry-dialog">
      <h2 mat-dialog-title>Extend Expiry Date</h2>
      <div mat-dialog-content>
        <p>Select a new expiry date for credential: <strong>{{ data.credential.id }}</strong></p>

        <mat-form-field appearance="outline" class="date-field">
          <mat-label>New Expiry Date</mat-label>
          <input matInput [matDatepicker]="picker" [formControl]="data.newExpiryDate" [min]="minDate">
          <mat-datepicker-toggle matIconSuffix [for]="picker"></mat-datepicker-toggle>
          <mat-datepicker #picker></mat-datepicker>
        </mat-form-field>
      </div>
      <div mat-dialog-actions class="dialog-actions">
        <button mat-button (click)="onCancel()">Cancel</button>
        <button mat-raised-button color="primary"
                (click)="onConfirm()"
                [disabled]="!data.newExpiryDate.value">
          <mat-icon>schedule</mat-icon>
          Extend Expiry
        </button>
      </div>
    </div>
  `,
  styles: [`
    .extend-expiry-dialog {
      font-family: 'Inter', sans-serif;
      min-width: 400px;
    }
    .date-field {
      width: 100%;
      margin-top: 16px;
    }
    .dialog-actions {
      gap: 12px;
    }
  `]
})
export class ExtendExpiryDialogComponent {
  minDate = new Date();

  constructor(
    public dialogRef: MatDialogRef<ExtendExpiryDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {}

  onCancel(): void {
    this.dialogRef.close();
  }

  onConfirm(): void {
    if (this.data.newExpiryDate.value) {
      const formattedDate = this.data.newExpiryDate.value.toISOString();
      this.dialogRef.close({ newExpiryDate: formattedDate });
    }
  }
}
