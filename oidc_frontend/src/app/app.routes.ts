import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'issue-credential', loadComponent: () => import('./components/issue-credential/issue-credential.component').then(m => m.IssueCredentialComponent) },
  { path: 'manage-credentials', loadComponent: () => import('./components/manage-credentials/manage-credentials.component').then(m => m.ManageCredentialsComponent) },
  { path: 'verification-logs', loadComponent: () => import('./components/verification-logs/verification-logs.component').then(m => m.VerificationLogsComponent) },
  { path: 'audit-health', loadComponent: () => import('./components/audit-health/audit-health.component').then(m => m.AuditHealthComponent) },
  { path: '**', redirectTo: '/dashboard' }
];
