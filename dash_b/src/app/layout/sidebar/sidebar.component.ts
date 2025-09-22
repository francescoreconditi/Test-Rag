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
    <mat-sidenav-container class="sidenav-container">
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
          <button
            mat-icon-button
            (click)="toggleCollapse()"
            class="collapse-btn"
            matTooltip="{{ isCollapsed ? 'Espandi' : 'Riduci' }}">
            <mat-icon>{{ isCollapsed ? 'chevron_right' : 'chevron_left' }}</mat-icon>
          </button>
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

              <mat-icon matListItemIcon [matBadge]="item.badge" [matBadgeHidden]="!item.badge">
                {{ item.icon }}
              </mat-icon>

              <span matListItemTitle *ngIf="!isCollapsed">{{ item.label }}</span>

              <span matListItemLine *ngIf="!isCollapsed && item.badge" class="badge-line">
                {{ getBadgeText(item.badge) }}
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
      height: 100vh;
      position: fixed;
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
      transition: width 0.3s ease;
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
        background: rgba(255, 255, 255, 0.15);
        color: white;
        position: relative;

        &::before {
          content: '';
          position: absolute;
          left: 0;
          top: 0;
          bottom: 0;
          width: 4px;
          background: #ff4081;
          border-radius: 0 4px 4px 0;
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

    .badge-line {
      font-size: 0.75rem;
      opacity: 0.8;
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
      margin-left: 280px;
      transition: margin-left 0.3s ease;

      &.collapsed {
        margin-left: 60px;
      }
    }

    mat-divider {
      background-color: rgba(255, 255, 255, 0.12);
      margin: 8px 0;
    }

    @media (max-width: 768px) {
      .sidenav-container {
        top: 56px;
      }

      .app-sidenav {
        position: fixed;
        z-index: 1001;
      }

      .sidenav-content {
        margin-left: 0;
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
  }

  toggleCollapse(): void {
    this.isCollapsed = !this.isCollapsed;
    this.sidenavWidth = this.isCollapsed ? 60 : 280;

    // Update content margin
    const content = document.querySelector('.sidenav-content') as HTMLElement;
    if (content) {
      content.style.marginLeft = `${this.sidenavWidth}px`;
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