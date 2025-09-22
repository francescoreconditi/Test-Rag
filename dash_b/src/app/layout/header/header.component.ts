import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { Subject, takeUntil } from 'rxjs';

import { ThemeService } from '../../core/services/theme.service';
import { NotificationService } from '../../core/services/notification.service';
import { ApiService } from '../../core/services/api.service';
import { Theme, NotificationMessage } from '../../core/models/ui.model';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatBadgeModule,
    MatSlideToggleModule,
    MatTooltipModule,
    MatDividerModule
  ],
  template: `
    <mat-toolbar class="app-toolbar" color="primary">
      <div class="toolbar-content">
        <!-- Left Section -->
        <div class="toolbar-left">
          <button mat-icon-button (click)="toggleSidebar()" matTooltip="Toggle Menu">
            <mat-icon>menu</mat-icon>
          </button>
          <h1 class="app-title">📊 RAG Dashboard</h1>
        </div>

        <!-- Right Section -->
        <div class="toolbar-right">
          <!-- Health Status -->
          <button
            mat-icon-button
            [color]="isHealthy ? 'primary' : 'warn'"
            (click)="checkHealth()"
            [matTooltip]="healthTooltip">
            <mat-icon>{{ isHealthy ? 'check_circle' : 'error' }}</mat-icon>
          </button>

          <!-- Theme Toggle -->
          <button
            mat-icon-button
            (click)="toggleTheme()"
            matTooltip="Toggle Dark Mode">
            <mat-icon>{{ isDarkMode ? 'light_mode' : 'dark_mode' }}</mat-icon>
          </button>

          <!-- Notifications -->
          <button
            mat-icon-button
            [matMenuTriggerFor]="notificationMenu"
            matTooltip="Notifications">
            <mat-icon [matBadge]="notificationCount" [matBadgeHidden]="notificationCount === 0">
              notifications
            </mat-icon>
          </button>

          <!-- User Menu -->
          <button
            mat-icon-button
            [matMenuTriggerFor]="userMenu"
            matTooltip="User Menu">
            <mat-icon>account_circle</mat-icon>
          </button>

          <!-- Loading Indicator -->
          <mat-icon *ngIf="isLoading" class="loading-spinner">refresh</mat-icon>
        </div>
      </div>
    </mat-toolbar>

    <!-- Notification Menu -->
    <mat-menu #notificationMenu="matMenu" class="notification-menu">
      <div class="menu-header">
        <span>Notifiche</span>
        <button mat-button (click)="clearAllNotifications()" *ngIf="notificationCount > 0">
          Cancella tutto
        </button>
      </div>
      <div class="notification-list" *ngIf="notifications.length > 0; else noNotifications">
        <div
          *ngFor="let notification of notifications.slice(0, 5)"
          class="notification-item"
          [ngClass]="'notification-' + notification.type">
          <div class="notification-content">
            <div class="notification-title">{{ notification.title }}</div>
            <div class="notification-message">{{ notification.message }}</div>
            <div class="notification-time">{{ formatTime(notification.timestamp) }}</div>
          </div>
          <button mat-icon-button (click)="removeNotification(notification.id)">
            <mat-icon>close</mat-icon>
          </button>
        </div>
      </div>
      <ng-template #noNotifications>
        <div class="no-notifications">Nessuna notifica</div>
      </ng-template>
    </mat-menu>

    <!-- User Menu -->
    <mat-menu #userMenu="matMenu">
      <button mat-menu-item>
        <mat-icon>person</mat-icon>
        <span>Profilo</span>
      </button>
      <button mat-menu-item>
        <mat-icon>settings</mat-icon>
        <span>Impostazioni</span>
      </button>
      <mat-divider></mat-divider>
      <button mat-menu-item>
        <mat-icon>help</mat-icon>
        <span>Aiuto</span>
      </button>
      <button mat-menu-item>
        <mat-icon>logout</mat-icon>
        <span>Logout</span>
      </button>
    </mat-menu>
  `,
  styles: [`
    .app-toolbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 1000;
      height: 64px;
    }

    .toolbar-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      height: 100%;
    }

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .app-title {
      margin: 0;
      font-size: 1.2rem;
      font-weight: 500;
    }

    .loading-spinner {
      animation: spin 1s linear infinite;
      color: rgba(255, 255, 255, 0.7);
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .notification-menu {
      min-width: 320px;
      max-width: 400px;
    }

    .menu-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #e0e0e0;
      font-weight: 600;
    }

    .notification-list {
      max-height: 400px;
      overflow-y: auto;
    }

    .notification-item {
      display: flex;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      transition: background-color 0.2s;

      &:hover {
        background-color: #f5f5f5;
      }

      &.notification-success {
        border-left: 4px solid #4caf50;
      }

      &.notification-error {
        border-left: 4px solid #f44336;
      }

      &.notification-warning {
        border-left: 4px solid #ff9800;
      }

      &.notification-info {
        border-left: 4px solid #2196f3;
      }
    }

    .notification-content {
      flex: 1;
    }

    .notification-title {
      font-weight: 600;
      font-size: 0.9rem;
      margin-bottom: 4px;
    }

    .notification-message {
      font-size: 0.8rem;
      color: #666;
      margin-bottom: 4px;
    }

    .notification-time {
      font-size: 0.75rem;
      color: #999;
    }

    .no-notifications {
      padding: 24px;
      text-align: center;
      color: #999;
      font-style: italic;
    }

    @media (max-width: 768px) {
      .app-title {
        display: none;
      }

      .toolbar-right {
        gap: 4px;
      }
    }
  `]
})
export class HeaderComponent implements OnInit, OnDestroy {
  isDarkMode = false;
  isHealthy = false;
  healthTooltip = 'Checking...';
  isLoading = false;
  notifications: NotificationMessage[] = [];
  notificationCount = 0;

  private destroy$ = new Subject<void>();

  constructor(
    private themeService: ThemeService,
    private notificationService: NotificationService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    // Subscribe to theme changes
    this.themeService.currentTheme$
      .pipe(takeUntil(this.destroy$))
      .subscribe(theme => {
        this.isDarkMode = theme.isDark;
      });

    // Subscribe to notifications
    this.notificationService.notifications$
      .pipe(takeUntil(this.destroy$))
      .subscribe(notifications => {
        this.notifications = notifications;
        this.notificationCount = notifications.length;
      });

    // Subscribe to loading state
    this.apiService.loading$
      .pipe(takeUntil(this.destroy$))
      .subscribe(loading => {
        this.isLoading = loading;
      });

    // Initial health check
    this.checkHealth();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  toggleSidebar(): void {
    // Emit event for sidebar toggle
    document.dispatchEvent(new CustomEvent('toggle-sidebar'));
  }

  toggleTheme(): void {
    this.themeService.toggleDarkMode();
  }

  checkHealth(): void {
    this.apiService.getHealthCheck().subscribe({
      next: (response) => {
        this.isHealthy = true;
        this.healthTooltip = 'API Server Online';
      },
      error: (error) => {
        this.isHealthy = false;
        this.healthTooltip = 'API Server Offline';
        this.notificationService.showError(
          'Connessione API',
          'Impossibile connettersi al server backend'
        );
      }
    });
  }

  removeNotification(id: string): void {
    this.notificationService.removeNotification(id);
  }

  clearAllNotifications(): void {
    this.notificationService.clearAll();
  }

  formatTime(timestamp: Date): string {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
      return `${days}g fa`;
    } else if (hours > 0) {
      return `${hours}h fa`;
    } else if (minutes > 0) {
      return `${minutes}m fa`;
    } else {
      return 'Ora';
    }
  }
}