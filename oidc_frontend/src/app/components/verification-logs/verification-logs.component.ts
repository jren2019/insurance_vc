import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { CredentialService } from '../../services/credential.service';
import { VerificationLog } from '../../models/credential.types';

@Component({
  selector: 'app-verification-logs',
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
    MatChipsModule
  ],
  template: `
    <div class="verification-logs">
      <!-- KPI Cards -->
      <div class="kpi-section">
        <div class="kpi-cards">
          <mat-card class="kpi-card total-checks">
            <div class="kpi-icon">
              <mat-icon>analytics</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Total Checks</div>
              <div class="kpi-value">852</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                +12.7% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card pass-rate">
            <div class="kpi-icon">
              <mat-icon>check_circle</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Pass Rate</div>
              <div class="kpi-value">96.4%</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                +1.3% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card failed-checks">
            <div class="kpi-icon">
              <mat-icon>error</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Failed Checks</div>
              <div class="kpi-value">31</div>
              <div class="kpi-change negative">
                <mat-icon>trending_down</mat-icon>
                -8.4% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card avg-response">
            <div class="kpi-icon">
              <mat-icon>schedule</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Avg Response</div>
              <div class="kpi-value">127ms</div>
              <div class="kpi-change negative">
                <mat-icon>trending_down</mat-icon>
                -23ms vs last 30 days
              </div>
            </div>
          </mat-card>
        </div>
      </div>

      <mat-card class="logs-table-card">
        <div class="card-header">
          <div class="header-content">
            <h2>Verification Logs</h2>
            <p>Track all credential verification attempts</p>
          </div>
        </div>

        <div class="table-header">
          <div class="search-filters">
            <mat-form-field appearance="outline" class="search-field">
              <mat-label>Search by credential ID or verifier...</mat-label>
              <input matInput>
              <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>All Results</mat-label>
              <mat-select>
                <mat-option value="all">All Results</mat-option>
                <mat-option value="PASS">Pass</mat-option>
                <mat-option value="FAIL">Fail</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="table-info">
            Showing {{ verificationLogs.length }} of {{ verificationLogs.length }} verification logs
          </div>
        </div>

        <div class="table-container">
          <table mat-table [dataSource]="verificationLogs" class="logs-table">
            <ng-container matColumnDef="checkedAt">
              <th mat-header-cell *matHeaderCellDef>Checked At</th>
              <td mat-cell *matCellDef="let log">{{ log.checkedAt }}</td>
            </ng-container>

            <ng-container matColumnDef="credentialId">
              <th mat-header-cell *matHeaderCellDef>Credential ID</th>
              <td mat-cell *matCellDef="let log">
                <a href="#" class="credential-link">{{ log.credentialId }}</a>
              </td>
            </ng-container>

            <ng-container matColumnDef="result">
              <th mat-header-cell *matHeaderCellDef>Result</th>
              <td mat-cell *matCellDef="let log">
                <mat-chip [class]="'result-' + log.result.toLowerCase()" class="result-chip">
                  {{ log.result }}
                </mat-chip>
              </td>
            </ng-container>

            <ng-container matColumnDef="responseTime">
              <th mat-header-cell *matHeaderCellDef>Response Time</th>
              <td mat-cell *matCellDef="let log">{{ log.responseTime }}ms</td>
            </ng-container>

            <ng-container matColumnDef="verifier">
              <th mat-header-cell *matHeaderCellDef>Verifier</th>
              <td mat-cell *matCellDef="let log">{{ log.verifier }}</td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="table-row"></tr>
          </table>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .verification-logs {
      max-width: 1400px;
      margin: 0 auto;
    }

    .kpi-section {
      margin-bottom: 32px;
    }

    .kpi-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 24px;
    }

    .kpi-card {
      padding: 24px;
      display: flex;
      align-items: center;
      gap: 16px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      border: 1px solid #e0e0e0;
    }

    .kpi-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .kpi-icon mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
      color: white;
    }

    .total-checks .kpi-icon { background: #8E44AD; }
    .pass-rate .kpi-icon { background: #27AE60; }
    .failed-checks .kpi-icon { background: #E74C3C; }
    .avg-response .kpi-icon { background: #F39C12; }

    .kpi-content {
      flex: 1;
    }

    .kpi-label {
      font-size: 14px;
      color: #7f8c8d;
      margin-bottom: 8px;
    }

    .kpi-value {
      font-size: 28px;
      font-weight: 700;
      color: #2c3e50;
      margin-bottom: 8px;
    }

    .kpi-change {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 500;
    }

    .kpi-change.positive {
      color: #27AE60;
    }

    .kpi-change.negative {
      color: #E74C3C;
    }

    .kpi-change mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .logs-table-card {
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      overflow: hidden;
    }

    .card-header {
      padding: 24px 24px 0 24px;
    }

    .header-content h2 {
      font-size: 20px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0 0 4px 0;
    }

    .header-content p {
      color: #7f8c8d;
      margin: 0;
      font-size: 14px;
    }

    .table-header {
      padding: 0 24px 16px 24px;
    }

    .search-filters {
      display: flex;
      gap: 16px;
      margin: 16px 0;
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

    .logs-table {
      width: 100%;
    }

    .logs-table th {
      font-weight: 600;
      color: #34495e;
      border-bottom: 2px solid #ecf0f1;
      padding: 16px;
    }

    .logs-table td {
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
    }

    .credential-link:hover {
      text-decoration: underline;
    }

    .result-chip {
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
      padding: 4px 12px;
      text-transform: uppercase;
    }

    .result-chip.result-pass {
      background-color: #d4edda;
      color: #155724;
    }

    .result-chip.result-fail {
      background-color: #f8d7da;
      color: #721c24;
    }
  `]
})
export class VerificationLogsComponent implements OnInit {
  verificationLogs: VerificationLog[] = [];
  displayedColumns = ['checkedAt', 'credentialId', 'result', 'responseTime', 'verifier'];

  constructor(private credentialService: CredentialService) {}

  ngOnInit() {
    this.loadVerificationLogs();
  }

  loadVerificationLogs() {
    this.credentialService.getVerificationLogs().subscribe(logs => {
      this.verificationLogs = logs;
    });
  }
}
