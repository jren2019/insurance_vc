import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { SidebarComponent } from './sidebar.component';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';

interface PageInfo {
  title: string;
  subtitle: string;
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatButtonModule, MatIconModule, SidebarComponent],
  template: `
    <div class="app-layout">
      <app-sidebar></app-sidebar>

      <div class="main-content">
        <header class="header">
          <div class="page-title">
            <h1>{{ currentPageInfo.title }}</h1>
            <p class="page-subtitle">{{ currentPageInfo.subtitle }}</p>
          </div>

          <div class="header-actions">
            <button mat-raised-button color="primary" class="action-btn issue-btn"
                    (click)="navigateToIssueCredential()">
              <mat-icon>add</mat-icon>
              Issue New
            </button>
            <button mat-raised-button color="accent" class="action-btn verify-btn">
              <mat-icon>verified_user</mat-icon>
              Verify
            </button>
            <button mat-raised-button class="action-btn manage-btn"
                    (click)="navigateToManageCredentials()">
              <mat-icon>settings</mat-icon>
              Manage
            </button>
          </div>
        </header>

        <div class="page-content">
          <router-outlet></router-outlet>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      height: 100vh;
      font-family: 'Inter', sans-serif;
    }

    .main-content {
      flex: 1;
      margin-left: 250px;
      display: flex;
      flex-direction: column;
      background: #f5f5f5;
    }

    .header {
      background: white;
      padding: 20px 32px;
      border-bottom: 1px solid #e0e0e0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .page-title h1 {
      font-size: 28px;
      font-weight: 600;
      color: #2c3e50;
      margin: 0;
      font-family: 'Inter', sans-serif;
    }

    .page-subtitle {
      font-size: 14px;
      color: #7f8c8d;
      margin: 4px 0 0 0;
      font-weight: 400;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .action-btn {
      height: 40px;
      border-radius: 6px;
      font-weight: 500;
      text-transform: none;
      font-family: 'Inter', sans-serif;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
    }

    .issue-btn {
      background: #4A90E2;
      color: white;
    }

    .verify-btn {
      background: #27AE60;
      color: white;
    }

    .manage-btn {
      background: #8E44AD;
      color: white;
    }

    .action-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .page-content {
      flex: 1;
      padding: 32px;
      overflow-y: auto;
    }

    /* Responsive design */
    @media (max-width: 768px) {
      .main-content {
        margin-left: 0;
      }

      .header {
        padding: 16px 20px;
        flex-direction: column;
        gap: 16px;
        align-items: flex-start;
      }

      .header-actions {
        width: 100%;
        justify-content: flex-end;
      }

      .action-btn {
        height: 36px;
        font-size: 14px;
      }

      .page-content {
        padding: 20px;
      }
    }
  `]
})
export class MainLayoutComponent implements OnInit, OnDestroy {
  currentPageInfo: PageInfo = {
    title: 'Dashboard',
    subtitle: 'Overview of your credential management system'
  };

  private routerSubscription: Subscription = new Subscription();

  // Page configuration mapping
  private pageConfig: { [key: string]: PageInfo } = {
    '/dashboard': {
      title: 'Dashboard',
      subtitle: 'Overview of your credential management system'
    },
    '/issue-credential': {
      title: 'Issue Credential',
      subtitle: 'Create and configure a new credential'
    },
    '/manage-credentials': {
      title: 'Manage Credentials',
      subtitle: 'View and manage all issued credentials'
    },
    '/verification-logs': {
      title: 'Verification Logs',
      subtitle: 'Track all credential verification attempts'
    },
    '/audit-health': {
      title: 'Audit & Health',
      subtitle: 'System activity history and health monitoring'
    }
  };

  constructor(private router: Router) {}

  ngOnInit() {
    // Set initial page info based on current route
    this.updatePageInfo(this.router.url);

    // Subscribe to router events to update page info on navigation
    this.routerSubscription = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.updatePageInfo(event.url);
      });
  }

  ngOnDestroy() {
    this.routerSubscription.unsubscribe();
  }

  private updatePageInfo(url: string): void {
    // Remove query parameters and fragments
    const cleanUrl = url.split('?')[0].split('#')[0];

    // Find matching page config
    const pageInfo = this.pageConfig[cleanUrl];

    if (pageInfo) {
      this.currentPageInfo = pageInfo;
    } else {
      // Default fallback
      this.currentPageInfo = {
        title: 'Dashboard',
        subtitle: 'Overview of your credential management system'
      };
    }
  }

  navigateToIssueCredential(): void {
    this.router.navigate(['/issue-credential']);
  }

  navigateToManageCredentials(): void {
    this.router.navigate(['/manage-credentials']);
  }
}
