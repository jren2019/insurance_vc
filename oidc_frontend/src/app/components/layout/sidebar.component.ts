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
      background: #2c3e50;
      color: white;
      width: 250px;
      height: 100vh;
      position: fixed;
      left: 0;
      top: 0;
      z-index: 1000;
      display: flex;
      flex-direction: column;
    }

    .logo-section {
      padding: 24px 20px;
      border-bottom: 1px solid #34495e;
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
      color: white;
      font-family: 'Inter', sans-serif;
    }

    .brand-subtitle {
      font-size: 12px;
      color: #bdc3c7;
      margin-top: 2px;
      font-weight: 400;
    }

    .version {
      font-size: 11px;
      color: #7f8c8d;
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
      color: #7f8c8d;
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
      color: #bdc3c7;
      text-decoration: none;
      transition: all 0.2s ease;
      border-left: 3px solid transparent;
      font-family: 'Inter', sans-serif;
    }

    .nav-link:hover {
      background: #34495e;
      color: white;
    }

    .nav-link.active {
      background: #3498db;
      color: white;
      border-left-color: #2980b9;
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
