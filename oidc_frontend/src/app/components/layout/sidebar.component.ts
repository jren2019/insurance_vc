import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule, MatListModule],
  template: `
    <div class="sidebar">
      <div class="logo-section">
        <div class="logo">
          <div class="stream-icon">
            <img src="assets/logo.png" alt="STREAM Logo" class="logo-img" />
          </div>
          <div class="brand-text">
            <div class="brand-subtitle">Digital Acceptance Platform</div>
            <div class="version">V1.113</div>
          </div>
        </div>
      </div>

      <nav class="navigation">
        <div class="nav-header">NAVIGATION</div>
        <ul class="nav-list">
          <li class="nav-item">
            <a routerLink="/dashboard" routerLinkActive="active" class="nav-link">
              <mat-icon>dashboard</mat-icon>
              <span>Dashboard</span>
            </a>
          </li>
          <li class="nav-item">
            <a routerLink="/issue-credential" routerLinkActive="active" class="nav-link">
              <mat-icon>add_circle_outline</mat-icon>
              <span>Issue Credential</span>
            </a>
          </li>
          <li class="nav-item">
            <a routerLink="/manage-credentials" routerLinkActive="active" class="nav-link">
              <mat-icon>assignment</mat-icon>
              <span>Manage Credentials</span>
            </a>
          </li>
          <li class="nav-item">
            <a routerLink="/verification-logs" routerLinkActive="active" class="nav-link">
              <mat-icon>visibility</mat-icon>
              <span>Verification Logs</span>
            </a>
          </li>
        </ul>
      </nav>
    </div>
  `,
  styles: [`
    .sidebar {
      background: white;
      color: #333;
      width: 250px;
      height: 100vh;
      position: fixed;
      left: 0;
      top: 0;
      z-index: 1000;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #e0e0e0;
    }

    .logo-section {
      padding: 24px 20px;
      border-bottom: 1px solid #e0e0e0;
    }

    .logo {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }

    .stream-icon {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
    }

    .logo-img {
      width: 100%;
      height: auto;
      display: block;
      object-fit: contain;
    }

    .brand-text {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .brand-name {
      font-size: 20px;
      font-weight: 700;
      color: #333;
      font-family: 'Inter', sans-serif;
    }

    .brand-subtitle {
      font-size: 12px;
      color: #666;
      margin-top: 2px;
      font-weight: 400;
    }

    .version {
      font-size: 11px;
      color: #999;
      margin-top: 4px;
      font-weight: 300;
    }

    .navigation {
      flex: 1;
      padding: 0;
    }

    .nav-header {
      padding: 20px 20px 12px 20px;
      font-size: 12px;
      font-weight: 600;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 1px;
      font-family: 'Inter', sans-serif;
    }

    .nav-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .nav-item {
      margin: 0;
    }

    .nav-link {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      color: #333;
      text-decoration: none;
      transition: all 0.2s ease;
      border-left: 3px solid transparent;
      font-family: 'Inter', sans-serif;
    }

    .nav-link:hover {
      background: #f5f5f5;
      color: #333;
    }

    .nav-link.active {
      background: #e3f2fd;
      color: #1976d2;
      border-left-color: #1976d2;
    }

    .nav-link mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: inherit;
    }

    .nav-link span {
      font-size: 14px;
      font-weight: 500;
    }
  `]
})
export class SidebarComponent {
}
