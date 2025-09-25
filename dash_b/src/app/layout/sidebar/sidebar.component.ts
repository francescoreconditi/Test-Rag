import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { Subject, takeUntil, filter } from 'rxjs';

import { NavigationItem } from '../../core/models/ui.model';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatBadgeModule,
    MatTooltipModule,
    MatDividerModule
  ],
  template: `
    <mat-sidenav-container class="sidenav-container"
                          [class.sidebar-collapsed]="isCollapsed"
                          [class.sidebar-closed]="!isOpen">
      <mat-sidenav
        #sidenav
        [opened]="isOpen"
        [mode]="sidenavMode"
        class="app-sidenav"
        [style.width.px]="sidenavWidth">

        <!-- Sidebar Header -->
        <div class="sidenav-header">
          <div class="logo-container">
            <mat-icon class="logo-icon">dashboard</mat-icon>
            <span class="logo-text" *ngIf="!isCollapsed">RAG Dashboard</span>
          </div>
        </div>

        <!-- Navigation Menu -->
        <mat-nav-list class="nav-list">
          <ng-container *ngFor="let item of navigationItems">
            <!-- Regular Nav Item -->
            <a
              mat-list-item
              [routerLink]="item.route"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{exact: item.route === '/'}"
              class="nav-item"
              [matTooltip]="isCollapsed ? item.label : ''"
              matTooltipPosition="right"
              [disabled]="item.disabled">

              <mat-icon matListItemIcon [attr.aria-hidden]="item.badge ? 'false' : 'true'">
                {{ item.icon }}
              </mat-icon>

              <span matListItemTitle *ngIf="!isCollapsed" class="nav-label">
                {{ item.label }}
                <span *ngIf="item.badge" class="pro-badge">{{ getBadgeText(item.badge) }}</span>
              </span>
            </a>

            <!-- Divider after specific items -->
            <mat-divider *ngIf="item.id === 'query' || item.id === 'enterprise'"></mat-divider>
          </ng-container>
        </mat-nav-list>

        <!-- Sidebar Footer -->
        <div class="sidenav-footer" *ngIf="!isCollapsed">
          <div class="stats-container">
            <div class="stat-item">
              <mat-icon>description</mat-icon>
              <span>{{ indexStats.total_documents || 0 }} Docs</span>
            </div>
            <div class="stat-item">
              <mat-icon>storage</mat-icon>
              <span>{{ formatVectorCount(indexStats.total_vectors) }} Vectors</span>
            </div>
          </div>
          <div class="version-info">
            v1.0.0
          </div>
        </div>
      </mat-sidenav>

      <mat-sidenav-content class="sidenav-content">
        <ng-content></ng-content>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: calc(100vh - 64px);
      position: absolute;
      top: 64px;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 999;
    }

    .app-sidenav {
      background: linear-gradient(180deg, #3f51b5 0%, #303f9f 100%);
      color: white;
      border-right: none;
      transition: none !important;
    }

    .sidenav-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.12);
      min-height: 64px;
    }

    .logo-container {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
    }

    .logo-text {
      font-size: 1.2rem;
      font-weight: 600;
      white-space: nowrap;
    }

    .collapse-btn {
      color: rgba(255, 255, 255, 0.7);

      &:hover {
        color: white;
        background: rgba(255, 255, 255, 0.1);
      }
    }

    .nav-list {
      padding: 8px 0;
      flex: 1;
    }

    .nav-item {
      color: rgba(255, 255, 255, 0.8);
      transition: all 0.3s ease;
      margin: 2px 8px;
      border-radius: 8px;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: white;
      }

      &.active {
        background: #ff4081 !important;
        color: white !important;
        font-weight: 600;
        position: relative;
        box-shadow:
          inset 0 0 0 2px rgba(255, 255, 255, 0.2),
          0 4px 12px rgba(255, 64, 129, 0.4) !important;
        border-radius: 8px !important;
        transform: translateX(4px);
        border: 2px solid rgba(255, 255, 255, 0.3) !important;

        &::before {
          content: '';
          position: absolute;
          left: -2px;
          top: -2px;
          bottom: -2px;
          width: 8px;
          background: #ffffff;
          border-radius: 0 10px 10px 0;
          box-shadow: 0 0 16px rgba(255, 255, 255, 0.8);
          z-index: 1;
        }

        &::after {
          content: '●';
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: #ffffff;
          font-size: 8px;
          text-shadow: 0 0 8px rgba(255, 255, 255, 1);
          z-index: 2;
        }

        mat-icon {
          color: white !important;
          text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
          z-index: 2;
          position: relative;
        }

        .nav-label {
          color: white !important;
          font-weight: 800;
          text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
          z-index: 2;
          position: relative;
        }

        &:hover {
          background: #e91e63 !important;
          transform: translateX(6px);
          box-shadow:
            inset 0 0 0 2px rgba(255, 255, 255, 0.3),
            0 6px 16px rgba(255, 64, 129, 0.6) !important;
        }
      }

      &[disabled] {
        opacity: 0.5;
        pointer-events: none;
      }

      mat-icon {
        color: inherit;
      }
    }

    .nav-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
    }

    .pro-badge {
      font-size: 0.65rem;
      background: rgba(255, 255, 255, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      margin-left: 8px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }

    .sidenav-footer {
      margin-top: auto;
      padding: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
    }

    .stats-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      color: rgba(255, 255, 255, 0.8);

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    .version-info {
      font-size: 0.75rem;
      text-align: center;
      color: rgba(255, 255, 255, 0.6);
    }

    .sidenav-content {
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      transition: none !important;
    }

    mat-divider {
      background-color: rgba(255, 255, 255, 0.12);
      margin: 8px 0;
    }

    // Disabilita completamente le animazioni del sidenav
    ::ng-deep .mat-drawer-transition .mat-drawer-content {
      transition: none !important;
      transform: none !important;
    }

    ::ng-deep .mat-drawer-transition .mat-drawer {
      transition: none !important;
      transform: none !important;
    }

    ::ng-deep .mat-sidenav-container {
      transition: none !important;
    }

    ::ng-deep .mat-sidenav-content {
      transition: none !important;
      margin-left: 0 !important;
    }

    @media (max-width: 768px) {
      .sidenav-container {
        top: 56px;
      }

      .app-sidenav {
        position: fixed;
        z-index: 1001;
      }
    }
  `]
})
export class SidebarComponent implements OnInit, OnDestroy {
  isOpen = true;
  isCollapsed = false;
  sidenavMode: 'side' | 'over' = 'side';
  sidenavWidth = 280;
  currentRoute = '';

  indexStats = {
    total_documents: 0,
    total_vectors: 0
  };

  navigationItems: NavigationItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'dashboard',
      route: '/dashboard'
    },
    {
      id: 'documents',
      label: 'Gestione Documenti',
      icon: 'folder',
      route: '/documents'
    },
    {
      id: 'csv-analysis',
      label: 'Analisi CSV',
      icon: 'table_chart',
      route: '/csv-analysis'
    },
    {
      id: 'query',
      label: 'Query RAG',
      icon: 'search',
      route: '/query'
    },
    {
      id: 'faq',
      label: 'FAQ Intelligenti',
      icon: 'quiz',
      route: '/faq'
    },
    {
      id: 'enterprise',
      label: 'Enterprise Mode',
      icon: 'business',
      route: '/enterprise',
      badge: 'PRO'
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: 'analytics',
      route: '/analytics'
    },
    {
      id: 'settings',
      label: 'Impostazioni',
      icon: 'settings',
      route: '/settings'
    }
  ];

  private destroy$ = new Subject<void>();

  constructor(
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    // Handle responsive behavior
    this.handleResize();
    window.addEventListener('resize', () => this.handleResize());

    // Listen for sidebar toggle events
    document.addEventListener('toggle-sidebar', () => {
      this.toggleSidebar();
    });

    // Track current route
    this.router.events
      .pipe(
        filter(event => event instanceof NavigationEnd),
        takeUntil(this.destroy$)
      )
      .subscribe((event: NavigationEnd) => {
        this.currentRoute = event.url;
      });

    // Load index stats
    this.loadIndexStats();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  toggleSidebar(): void {
    this.isOpen = !this.isOpen;
    // Force update of content margin when sidebar is toggled
    this.updateContentMargin();
  }

  toggleCollapse(): void {
    this.isCollapsed = !this.isCollapsed;
    this.sidenavWidth = this.isCollapsed ? 60 : 280;
    this.updateContentMargin();
  }

  private updateContentMargin(): void {
    // Update content margin based on sidebar state
    const container = document.querySelector('.sidenav-container') as HTMLElement;
    if (container) {
      // Use CSS classes for better responsive behavior
      container.classList.toggle('sidebar-collapsed', this.isCollapsed);
      container.classList.toggle('sidebar-closed', !this.isOpen);
    }
  }

  getBadgeText(badge: string | number | undefined): string {
    if (!badge) return '';
    return typeof badge === 'number' ? badge.toString() : badge;
  }

  formatVectorCount(count: number): string {
    if (count < 1000) return count.toString();
    if (count < 1000000) return `${(count / 1000).toFixed(1)}K`;
    return `${(count / 1000000).toFixed(1)}M`;
  }

  private handleResize(): void {
    const width = window.innerWidth;
    if (width <= 768) {
      this.sidenavMode = 'over';
      this.isOpen = false;
    } else {
      this.sidenavMode = 'side';
      this.isOpen = true;
    }
  }

  private loadIndexStats(): void {
    this.apiService.getIndexStats().subscribe({
      next: (stats) => {
        this.indexStats = stats;
      },
      error: (error) => {
        console.warn('Failed to load index stats:', error);
      }
    });
  }
}