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
import { SystemHealth, AuditEntry } from '../../models/credential.types';

@Component({
  selector: 'app-audit-health',
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
    <div class="audit-health">
      <!-- System Health KPIs -->
      <div class="kpi-section">
        <div class="kpi-cards">
          <mat-card class="kpi-card api-uptime">
            <div class="kpi-icon">
              <mat-icon>dns</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">API Uptime</div>
              <div class="kpi-value">{{ systemHealth?.apiUptime }}%</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                {{ systemHealth?.uptimeChange }} vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card system-status">
            <div class="kpi-icon">
              <mat-icon>health_and_safety</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">System Status</div>
              <div class="kpi-value status-healthy">{{ systemHealth?.systemStatus }}</div>
              <div class="kpi-change">
                <mat-icon>check_circle</mat-icon>
                All systems operational
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card avg-response">
            <div class="kpi-icon">
              <mat-icon>speed</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Avg Response</div>
              <div class="kpi-value">{{ systemHealth?.avgResponse }}ms</div>
              <div class="kpi-change negative">
                <mat-icon>trending_down</mat-icon>
                {{ systemHealth?.avgResponseChange }} vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card active-sessions">
            <div class="kpi-icon">
              <mat-icon>people</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Active Sessions</div>
              <div class="kpi-value">{{ systemHealth?.activeSessions }}</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                {{ systemHealth?.activeSessionsChange }} vs last 30 days
              </div>
            </div>
          </mat-card>
        </div>
      </div>

      <mat-card class="audit-table-card">
        <div class="card-header">
          <div class="header-content">
            <h2>Audit & Health</h2>
            <p>System activity history</p>
          </div>
        </div>

        <div class="table-header">
          <div class="search-filters">
            <mat-form-field appearance="outline" class="search-field">
              <mat-label>Search by details, credential ID, or user...</mat-label>
              <input matInput>
              <mat-icon matPrefix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline" class="filter-field">
              <mat-label>All Actions</mat-label>
              <mat-select>
                <mat-option value="all">All Actions</mat-option>
                <mat-option value="Credential Revoke">Credential Revoke</mat-option>
                <mat-option value="Credential Issue">Credential Issue</mat-option>
                <mat-option value="Credential Extend">Credential Extend</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <div class="table-info">
            Showing 68 of 68 log entries
          </div>
        </div>

        <div class="table-container">
          <table mat-table [dataSource]="auditEntries" class="audit-table">
            <ng-container matColumnDef="timestamp">
              <th mat-header-cell *matHeaderCellDef>Timestamp</th>
              <td mat-cell *matCellDef="let entry">{{ entry.timestamp }}</td>
            </ng-container>

            <ng-container matColumnDef="action">
              <th mat-header-cell *matHeaderCellDef>Action</th>
              <td mat-cell *matCellDef="let entry">
                <mat-chip
                  [class]="getActionClass(entry.action)"
                  class="action-chip">
                  {{ entry.action }}
                </mat-chip>
              </td>
            </ng-container>

            <ng-container matColumnDef="user">
              <th mat-header-cell *matHeaderCellDef>User</th>
              <td mat-cell *matCellDef="let entry">{{ entry.user }}</td>
            </ng-container>

            <ng-container matColumnDef="credentialId">
              <th mat-header-cell *matHeaderCellDef>Credential ID</th>
              <td mat-cell *matCellDef="let entry">
                <a href="#" class="credential-link">{{ entry.credentialId }}</a>
              </td>
            </ng-container>

            <ng-container matColumnDef="details">
              <th mat-header-cell *matHeaderCellDef>Details</th>
              <td mat-cell *matCellDef="let entry">{{ entry.details }}</td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="table-row"></tr>
          </table>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .audit-health {
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

    .api-uptime .kpi-icon { background: #27AE60; }
    .system-status .kpi-icon { background: #3498db; }
    .avg-response .kpi-icon { background: #8E44AD; }
    .active-sessions .kpi-icon { background: #F39C12; }

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

    .kpi-value.status-healthy {
      color: #27AE60;
    }

    .kpi-change {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 500;
      color: #7f8c8d;
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

    .audit-table-card {
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

    .audit-table {
      width: 100%;
    }

    .audit-table th {
      font-weight: 600;
      color: #34495e;
      border-bottom: 2px solid #ecf0f1;
      padding: 16px;
    }

    .audit-table td {
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

    .action-chip {
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
      padding: 4px 12px;
    }

    .action-chip.credential-revoke {
      background-color: #ffebee;
      color: #c62828;
    }

    .action-chip.credential-issue {
      background-color: #e8f5e8;
      color: #2e7d32;
    }

    .action-chip.credential-extend {
      background-color: #fff3e0;
      color: #f57c00;
    }
  `]
})
export class AuditHealthComponent implements OnInit {
  systemHealth: SystemHealth | null = null;
  auditEntries: AuditEntry[] = [
    {
      id: '1',
      timestamp: 'Aug 17, 2025 04:38:06',
      action: 'Credential Revoke',
      user: 'System Admin',
      credentialId: 'ACC-418277-QLK0',
      details: 'Revoked Account credential'
    },
    {
      id: '2',
      timestamp: 'Aug 17, 2025 04:37:11',
      action: 'Credential Issue',
      user: 'System Admin',
      credentialId: 'ACC-418277-QLK0',
      details: 'Issued Account credential (iso_mdoc)'
    },
    {
      id: '3',
      timestamp: 'Aug 12, 2025 05:35:25',
      action: 'Credential Issue',
      user: 'System Admin',
      credentialId: 'CUS-919371-AZ5X',
      details: 'Issued Custom credential'
    }
  ];

  displayedColumns = ['timestamp', 'action', 'user', 'credentialId', 'details'];

  constructor(private credentialService: CredentialService) {}

  ngOnInit() {
    this.loadSystemHealth();
  }

  loadSystemHealth() {
    this.credentialService.getSystemHealth().subscribe(health => {
      this.systemHealth = health;
    });
  }

  getActionClass(action: string): string {
    return action.toLowerCase().replace(' ', '-');
  }
}
