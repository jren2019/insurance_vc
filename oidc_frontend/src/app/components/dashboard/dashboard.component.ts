import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { CredentialService } from '../../services/credential.service';
import { CredentialMetrics, ActivityEntry } from '../../models/credential.types';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule
  ],
  template: `
    <div class="dashboard">
      <!-- KPI Cards -->
      <div class="kpi-section">
        <div class="kpi-cards">
          <mat-card class="kpi-card active-credentials">
            <div class="kpi-icon">
              <mat-icon>assignment</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Active Credentials</div>
              <div class="kpi-value">{{ metrics?.activeCredentials }}</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                {{ metrics?.passRateChange }} vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card new-credentials">
            <div class="kpi-icon">
              <mat-icon>add_circle</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">New Credentials</div>
              <div class="kpi-value">{{ metrics?.newCredentials }}</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                +5.4% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card total-verifications">
            <div class="kpi-icon">
              <mat-icon>verified</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Total Verifications</div>
              <div class="kpi-value">{{ metrics?.totalVerifications }}</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                +12.7% vs last 30 days
              </div>
            </div>
          </mat-card>
        </div>

        <div class="kpi-cards">
          <mat-card class="kpi-card pass-rate">
            <div class="kpi-icon">
              <mat-icon>check_circle</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Pass Rate</div>
              <div class="kpi-value">{{ metrics?.passRate }}%</div>
              <div class="kpi-change positive">
                <mat-icon>trending_up</mat-icon>
                +1.3% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card fail-rate">
            <div class="kpi-icon">
              <mat-icon>error</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Fail Rate</div>
              <div class="kpi-value">{{ metrics?.failRate }}%</div>
              <div class="kpi-change negative">
                <mat-icon>trending_down</mat-icon>
                -1.3% vs last 30 days
              </div>
            </div>
          </mat-card>

          <mat-card class="kpi-card avg-response">
            <div class="kpi-icon">
              <mat-icon>schedule</mat-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-label">Avg Response Time</div>
              <div class="kpi-value">{{ metrics?.avgResponseTime }}ms</div>
              <div class="kpi-change negative">
                <mat-icon>trending_down</mat-icon>
                {{ metrics?.avgResponseTimeChange }} vs last 30 days
              </div>
            </div>
          </mat-card>
        </div>
      </div>

      <!-- Recent Activity -->
      <mat-card class="activity-card">
        <div class="card-header">
          <h2>Recent Activity</h2>
        </div>

        <div class="table-container">
          <table mat-table [dataSource]="recentActivity" class="activity-table">
            <ng-container matColumnDef="action">
              <th mat-header-cell *matHeaderCellDef>Action</th>
              <td mat-cell *matCellDef="let activity">
                <mat-chip
                  [class]="getActionClass(activity.action)"
                  class="action-chip">
                  {{ activity.action }}
                </mat-chip>
              </td>
            </ng-container>

            <ng-container matColumnDef="details">
              <th mat-header-cell *matHeaderCellDef>Details</th>
              <td mat-cell *matCellDef="let activity">{{ activity.details }}</td>
            </ng-container>

            <ng-container matColumnDef="credentialId">
              <th mat-header-cell *matHeaderCellDef>Credential ID</th>
              <td mat-cell *matCellDef="let activity">
                <a href="#" class="credential-link">{{ activity.credentialId }}</a>
              </td>
            </ng-container>

            <ng-container matColumnDef="user">
              <th mat-header-cell *matHeaderCellDef>User</th>
              <td mat-cell *matCellDef="let activity">{{ activity.user }}</td>
            </ng-container>

            <ng-container matColumnDef="timestamp">
              <th mat-header-cell *matHeaderCellDef>Timestamp</th>
              <td mat-cell *matCellDef="let activity">{{ activity.timestamp }}</td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
          </table>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .dashboard {
      max-width: 1400px;
      margin: 0 auto;
    }

    .kpi-section {
      margin-bottom: 32px;
    }

    .kpi-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 24px;
      margin-bottom: 24px;
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

    .active-credentials .kpi-icon { background: #4A90E2; }
    .new-credentials .kpi-icon { background: #27AE60; }
    .total-verifications .kpi-icon { background: #8E44AD; }
    .pass-rate .kpi-icon { background: #27AE60; }
    .fail-rate .kpi-icon { background: #E74C3C; }
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

    .activity-card {
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      border: 1px solid #e0e0e0;
    }

    .card-header {
      padding: 24px 24px 0 24px;
    }

    .card-header h2 {
      font-size: 20px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0;
    }

    .table-container {
      padding: 0 24px 24px 24px;
    }

    .activity-table {
      width: 100%;
      margin-top: 16px;
    }

    .activity-table th {
      font-weight: 600;
      color: #34495e;
      border-bottom: 2px solid #ecf0f1;
    }

    .activity-table td {
      padding: 16px 8px;
      border-bottom: 1px solid #ecf0f1;
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

    .credential-link {
      color: #4A90E2;
      text-decoration: none;
      font-weight: 500;
    }

    .credential-link:hover {
      text-decoration: underline;
    }
  `]
})
export class DashboardComponent implements OnInit {
  metrics: CredentialMetrics | null = null;
  recentActivity: ActivityEntry[] = [];
  displayedColumns = ['action', 'details', 'credentialId', 'user', 'timestamp'];

  constructor(private credentialService: CredentialService) {}

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.credentialService.getMetrics().subscribe(metrics => {
      this.metrics = metrics;
    });

    this.credentialService.getRecentActivity().subscribe(activity => {
      this.recentActivity = activity;
    });
  }

  getActionClass(action: string): string {
    return action.toLowerCase().replace(' ', '-');
  }
}
