import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CredentialService } from '../../services/credential.service';
import { IssueCredentialForm } from '../../models/credential.types';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { Inject } from '@angular/core';

@Component({
  selector: 'app-issue-credential',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    ReactiveFormsModule,
    MatDialogModule
  ],
  template: `
    <div class="issue-credential">

      <mat-card class="credential-form-card">
        <form [formGroup]="credentialForm" (ngSubmit)="onSubmit()">
          <div class="form-section">
            <div class="form-row">
              <mat-form-field appearance="outline" class="form-field">
                <mat-label>Credential Type</mat-label>
                <mat-select formControlName="type" required>
                  <mat-option value="Account">Account</mat-option>
                  <mat-option value="Custom">Custom</mat-option>
                  <mat-option value="Membership">Membership</mat-option>
                  <mat-option value="Identity">Identity</mat-option>
                  <mat-option value="Employment">Employment</mat-option>
                </mat-select>
                <mat-error *ngIf="credentialForm.get('type')?.hasError('required')">
                  Credential type is required
                </mat-error>
              </mat-form-field>

              <mat-form-field appearance="outline" class="form-field">
                <mat-label>Format</mat-label>
                <mat-select formControlName="format" required>
                  <mat-option value="W3C VC (JWT)">
                    <div class="format-option-content">
                      <span class="format-title">W3C VC (JWT)</span>
                      <span class="format-subtitle">JSON Web Token format</span>
                    </div>
                  </mat-option>
                  <mat-option value="ISO mdoc">
                    <div class="format-option-content">
                      <span class="format-title">ISO mdoc</span>
                      <span class="format-subtitle">Mobile document format</span>
                    </div>
                  </mat-option>
                </mat-select>
                <mat-hint>Choose the credential format to issue</mat-hint>
                <mat-error *ngIf="credentialForm.get('format')?.hasError('required')">
                  Format is required
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="form-field full-width">
                <mat-label>Account ID</mat-label>
                <input matInput formControlName="accountId" placeholder="ACC-123456" required>
                <mat-hint>Enter the account identifier to fetch subject details</mat-hint>
                <mat-error *ngIf="credentialForm.get('accountId')?.hasError('required')">
                  Account ID is required
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="form-field full-width">
                <mat-label>Subject ID</mat-label>
                <input matInput formControlName="subjectId" placeholder="did:org.issuance-vc.bank.account:holder" required>
                <mat-hint>Identifier of the person or wallet that will hold this credential</mat-hint>
                <mat-error *ngIf="credentialForm.get('subjectId')?.hasError('required')">
                  Subject ID is required
                </mat-error>
                <mat-error *ngIf="credentialForm.get('subjectId')?.hasError('pattern')">
                  Subject ID must start with 'did:'
                </mat-error>
              </mat-form-field>
            </div>

            <div class="form-row">
              <mat-form-field appearance="outline" class="form-field">
                <mat-label>Valid From</mat-label>
                <input matInput [matDatepicker]="validFromPicker" formControlName="validFrom" required>
                <mat-datepicker-toggle matIconSuffix [for]="validFromPicker"></mat-datepicker-toggle>
                <mat-datepicker #validFromPicker></mat-datepicker>
                <mat-hint>Start date/time when this credential becomes valid</mat-hint>
                <mat-error *ngIf="credentialForm.get('validFrom')?.hasError('required')">
                  Valid from date is required
                </mat-error>
              </mat-form-field>

              <mat-form-field appearance="outline" class="form-field">
                <mat-label>Expiration Date (Optional)</mat-label>
                <input matInput [matDatepicker]="expirationPicker" formControlName="expirationDate">
                <mat-datepicker-toggle matIconSuffix [for]="expirationPicker"></mat-datepicker-toggle>
                <mat-datepicker #expirationPicker></mat-datepicker>
              </mat-form-field>
            </div>

            <div class="claims-section">
              <div class="claims-header">
                <h3>Claims</h3>
                <p>Key-value claims included in the credential</p>
              </div>

              <div formArrayName="claims" class="claims-list">
                <div *ngFor="let claim of claims.controls; let i = index"
                     [formGroupName]="i" class="claim-row">
                  <mat-form-field appearance="outline" class="claim-key">
                    <mat-label>Key</mat-label>
                    <input matInput formControlName="key">
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="claim-value">
                    <mat-label>Value</mat-label>
                    <input matInput formControlName="value">
                  </mat-form-field>

                  <button type="button" mat-icon-button color="warn"
                          (click)="removeClaim(i)" class="remove-claim"
                          [disabled]="isSubmitting">
                    <mat-icon>delete</mat-icon>
                  </button>
                </div>
              </div>

              <button type="button" mat-stroked-button (click)="addClaim()"
                      class="add-claim-btn" [disabled]="isSubmitting">
                <mat-icon>add</mat-icon>
                Add Claim
              </button>
            </div>

            <div class="form-actions">
              <button type="button" mat-stroked-button class="preview-btn"
                      [disabled]="isSubmitting" (click)="previewCredential()">
                <mat-icon>visibility</mat-icon>
                Preview & Issue
              </button>
              <button type="submit" mat-raised-button color="primary"
                      class="issue-btn" [disabled]="isSubmitting || credentialForm.invalid">
                <mat-icon *ngIf="isSubmitting; else issueIcon">
                  <mat-spinner diameter="20"></mat-spinner>
                </mat-icon>
                <ng-template #issueIcon>
                  <mat-icon>add_circle</mat-icon>
                </ng-template>
                {{ isSubmitting ? 'Issuing...' : 'Issue Credential' }}
              </button>
            </div>
          </div>
        </form>

        <!-- Loading Overlay -->
        <div *ngIf="isSubmitting" class="loading-overlay">
          <mat-spinner diameter="50"></mat-spinner>
          <p>{{ loadingMessage }}</p>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .issue-credential {
      max-width: 800px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 32px;
    }

    .page-header h1 {
      font-size: 28px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0 0 8px 0;
    }

    .page-header p {
      color: #7f8c8d;
      margin: 0;
    }

    .credential-form-card {
      padding: 32px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      position: relative;
    }

    .form-section {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .form-row {
      display: flex;
      gap: 24px;
      align-items: flex-start;
    }

    .form-field {
      flex: 1;
    }

    .form-field.full-width {
      flex: 1;
    }

    /* Format dropdown option styling */
    .format-option-content {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .format-title {
      font-weight: 500;
      color: #2c3e50;
      font-size: 14px;
    }

    .format-subtitle {
      font-size: 12px;
      color: #7f8c8d;
      line-height: 1.2;
    }

    .claims-section {
      border-top: 1px solid #e0e0e0;
      padding-top: 24px;
    }

    .claims-header h3 {
      font-size: 18px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0 0 4px 0;
    }

    .claims-header p {
      color: #7f8c8d;
      margin: 0 0 16px 0;
      font-size: 14px;
    }

    .claims-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-bottom: 16px;
    }

    .claim-row {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }

    .claim-key,
    .claim-value {
      flex: 1;
    }

    .remove-claim {
      margin-top: 8px;
    }

    .add-claim-btn {
      align-self: flex-start;
    }

    .form-actions {
      display: flex;
      gap: 16px;
      justify-content: flex-end;
      border-top: 1px solid #e0e0e0;
      padding-top: 24px;
    }

    .preview-btn,
    .issue-btn {
      height: 48px;
      border-radius: 8px;
      font-weight: 500;
      text-transform: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .issue-btn {
      background: #4A90E2;
      color: white;
    }

    .issue-btn:disabled {
      background: #bdc3c7;
      color: #7f8c8d;
    }

    .loading-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.9);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      z-index: 10;
      border-radius: 12px;
    }

    .loading-overlay p {
      color: #7f8c8d;
      font-weight: 500;
      font-size: 16px;
    }

    /* Responsive design */
    @media (max-width: 768px) {
      .form-row {
        flex-direction: column;
      }

      .credential-form-card {
        padding: 20px;
      }

      .form-actions {
        flex-direction: column;
        gap: 12px;
      }

      .preview-btn,
      .issue-btn {
        width: 100%;
      }
    }
  `]
})
export class IssueCredentialComponent {
  credentialForm: FormGroup;
  isSubmitting = false;
  loadingMessage = '';

  constructor(
    private fb: FormBuilder,
    private credentialService: CredentialService,
    private snackBar: MatSnackBar,
    private router: Router,
    private dialog: MatDialog
  ) {
    this.credentialForm = this.fb.group({
      type: ['Account', [Validators.required]],
      format: ['ISO mdoc', [Validators.required]],
      subjectId: ['did:org.issuance-vc.bank.account:holder', [Validators.required, Validators.pattern(/^did:.*$/)]],
      validFrom: ['', [Validators.required]],
      expirationDate: [''],
      accountId: ['', [Validators.required]],
      claims: this.fb.array([
        this.createClaimGroup()
      ])
    });
  }

  get claims(): FormArray {
    return this.credentialForm.get('claims') as FormArray;
  }

  createClaimGroup(): FormGroup {
    return this.fb.group({
      key: [''],
      value: ['']
    });
  }

  addClaim(): void {
    this.claims.push(this.createClaimGroup());
  }

  removeClaim(index: number): void {
    if (this.claims.length > 1) {
      this.claims.removeAt(index);
    }
  }

  previewCredential(): void {
    if (this.credentialForm.valid) {
      console.log('Preview credential:', this.credentialForm.value);
      this.showSuccessMessage('Credential preview generated. Ready to issue!');
    } else {
      this.showErrorMessage('Please fill in all required fields before preview.');
    }
  }

  onSubmit(): void {
    if (this.credentialForm.valid) {
      this.isSubmitting = true;
      this.loadingMessage = 'Creating credential...';

      // Prepare form data
      const formData = this.credentialForm.value;
      const credentialData: IssueCredentialForm = {
        type: formData.type,
        format: formData.format,
        subjectId: formData.subjectId,
        validFrom: formData.validFrom ? new Date(formData.validFrom).toISOString() : '',
        expirationDate: formData.expirationDate ? new Date(formData.expirationDate).toISOString() : undefined,
        claims: formData.claims.filter((claim: any) => claim.key && claim.value),
        accountId: formData.accountId
      };

      // Call API endpoint /issue_credential
      this.credentialService.issueCredential(credentialData).subscribe({
        next: (response) => {
          this.isSubmitting = false;
          this.loadingMessage = '';

          // Show success message
          this.showSuccessMessage(
            `${response.message} - Credential ID: ${response.credentialId}`
          );

          // Show demo dialog with mdoc and proof
          this.dialog.open(MdocPreviewDialogComponent, {
            width: '900px',
            maxHeight: '80vh',
            data: {
              credentialId: response.credentialId,
              mdoc: response.mdoc,
              jwk: response.jwk,
              proof_jwt: response.proof_jwt
            }
          });

          // Reset form
          this.resetForm();

          // Optional: Navigate to manage credentials page
          setTimeout(() => {
            this.router.navigate(['/manage-credentials']);
          }, 2000);
        },
        error: (error) => {
          this.isSubmitting = false;
          this.loadingMessage = '';
          this.showErrorMessage('Failed to issue credential: ' + error.message);
        }
      });
    } else {
      // Mark all fields as touched to show validation errors
      this.markFormGroupTouched(this.credentialForm);
      this.showErrorMessage('Please fill in all required fields correctly.');
    }
  }

  private resetForm(): void {
    this.credentialForm.reset();
    this.credentialForm.patchValue({
      type: 'Account',
      format: 'ISO mdoc',
      subjectId: 'did:org.issuance-vc.bank.account:holder',
      accountId: ''
    });

    // Reset claims array to have one empty claim
    while (this.claims.length > 1) {
      this.claims.removeAt(1);
    }
    this.claims.at(0)?.reset();
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach(field => {
      const control = formGroup.get(field);
      control?.markAsTouched({ onlySelf: true });

      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }

  private showSuccessMessage(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['success-snackbar']
    });
  }

  private showErrorMessage(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar']
    });
  }
}

@Component({
  selector: 'app-mdoc-preview-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule
  ],
  template: `
    <h2>Credential Details</h2>
    <p><strong>Credential ID:</strong> {{ data.credentialId }}</p>
    <h3>MDoc (Base64URL)</h3>
    <pre>{{ data.mdoc.base64url }}</pre>
    <h3>MDoc (Hex)</h3>
    <pre>{{ data.mdoc.hex }}</pre>
    <h3>JWK</h3>
    <pre>{{ data.jwk | json }}</pre>
    <h3>Proof JWT</h3>
    <pre>{{ data.proof_jwt }}</pre>
    <button mat-button (click)="dialogRef.close()">Close</button>
  `,
  styles: [`
    h2 {
      color: #2c3e50;
      margin-top: 0;
      margin-bottom: 16px;
    }

    p {
      color: #34495e;
      margin-bottom: 16px;
    }

    pre {
      background-color: #f5f5f5;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 14px;
      line-height: 1.5;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    button {
      background-color: #4A90E2;
      color: white;
      padding: 10px 20px;
      border-radius: 8px;
      font-weight: 500;
      text-transform: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    button:hover {
      background-color: #357abd;
    }
  `]
})
export class MdocPreviewDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<MdocPreviewDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { credentialId: string; mdoc: { base64url: string; hex: string }; jwk: any; proof_jwt: string }
  ) {}
}
