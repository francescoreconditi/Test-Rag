/**
 * Main Dashboard Component
 * Enterprise RAG System Dashboard with real-time statistics
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { Subscription, timer } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { RagService } from '../../services/rag.service';
import { UserContext, TenantContext } from '../../models/user-context';

interface DashboardStats {
  total_documents: number;
  total_vectors: number;
  total_queries: number;
  system_health: string;
  last_updated: Date;
  enterprise_mode: boolean;
  processing_time_avg: number;
  success_rate: number;
}

interface RecentActivity {
  id: string;
  type: 'query' | 'upload' | 'export';
  description: string;
  timestamp: Date;
  status: 'success' | 'error' | 'processing';
  user_email: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
  standalone: true,
  imports: [CommonModule]
})
export class DashboardComponent implements OnInit, OnDestroy {
  currentUser: UserContext | null = null;
  currentTenant: TenantContext | null = null;

  stats: DashboardStats = {
    total_documents: 0,
    total_vectors: 0,
    total_queries: 0,
    system_health: 'unknown',
    last_updated: new Date(),
    enterprise_mode: false,
    processing_time_avg: 0,
    success_rate: 0
  };

  recentActivities: RecentActivity[] = [];
  isLoading = true;
  error: string | null = null;

  private subscriptions = new Subscription();

  constructor(
    private authService: AuthService,
    private ragService: RagService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadUserContext();
    this.loadDashboardData();
    this.startAutoRefresh();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  /**
   * Load current user and tenant context
   */
  private loadUserContext(): void {
    this.subscriptions.add(
      this.authService.authState$.subscribe(state => {
        this.currentUser = state.user;
        this.currentTenant = state.currentTenant;
      })
    );
  }

  /**
   * Load dashboard statistics and recent activities
   */
  private loadDashboardData(): void {
    this.isLoading = true;
    this.error = null;

    // Load statistics
    this.subscriptions.add(
      this.ragService.getDashboardStats().subscribe({
        next: (stats) => {
          this.stats = {
            ...stats,
            last_updated: new Date()
          };
          this.isLoading = false;
        },
        error: (error) => {
          this.error = 'Failed to load dashboard statistics: ' + error.message;
          this.isLoading = false;
        }
      })
    );

    // Load recent activities
    this.subscriptions.add(
      this.ragService.getRecentActivities(10).subscribe({
        next: (activities) => {
          this.recentActivities = activities;
        },
        error: (error) => {
          console.warn('Failed to load recent activities:', error);
        }
      })
    );
  }

  /**
   * Start auto-refresh timer for dashboard data
   */
  private startAutoRefresh(): void {
    // Refresh every 30 seconds
    this.subscriptions.add(
      timer(30000, 30000).subscribe(() => {
        this.loadDashboardData();
      })
    );
  }

  /**
   * Manual refresh
   */
  refreshDashboard(): void {
    this.loadDashboardData();
  }

  /**
   * Toggle enterprise mode
   */
  toggleEnterpriseMode(): void {
    if (!this.hasEnterpriseAccess()) {
      this.error = 'Enterprise mode requires Professional or Enterprise tier';
      return;
    }

    this.subscriptions.add(
      this.ragService.toggleEnterpriseMode(!this.stats.enterprise_mode).subscribe({
        next: (result) => {
          this.stats.enterprise_mode = result.enterprise_mode;
        },
        error: (error) => {
          this.error = 'Failed to toggle enterprise mode: ' + error.message;
        }
      })
    );
  }

  /**
   * Navigate to documents page
   */
  goToDocuments(): void {
    this.router.navigate(['/documents']);
  }

  /**
   * Navigate to analytics page
   */
  goToAnalytics(): void {
    this.router.navigate(['/analytics']);
  }

  /**
   * Navigate to export page
   */
  goToExport(): void {
    this.router.navigate(['/export']);
  }

  /**
   * Navigate to security dashboard (admin only)
   */
  goToSecurity(): void {
    if (this.authService.hasMinRole('admin' as any)) {
      this.router.navigate(['/security']);
    }
  }

  /**
   * Logout current user
   */
  logout(): void {
    this.authService.logout();
  }

  /**
   * Get system health status color
   */
  getHealthStatusClass(): string {
    switch (this.stats.system_health) {
      case 'healthy': return 'status-healthy';
      case 'warning': return 'status-warning';
      case 'error': return 'status-error';
      default: return 'status-unknown';
    }
  }

  /**
   * Get system health icon
   */
  getHealthStatusIcon(): string {
    switch (this.stats.system_health) {
      case 'healthy': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return '❓';
    }
  }

  /**
   * Get activity status icon
   */
  getActivityStatusIcon(status: string): string {
    switch (status) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'processing': return '🔄';
      default: return '❓';
    }
  }

  /**
   * Get activity type icon
   */
  getActivityTypeIcon(type: string): string {
    switch (type) {
      case 'query': return '🔍';
      case 'upload': return '📄';
      case 'export': return '📊';
      default: return '📝';
    }
  }

  /**
   * Format large numbers
   */
  formatNumber(num: number): string {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  /**
   * Check if user has enterprise access
   */
  hasEnterpriseAccess(): boolean {
    return this.currentTenant?.tier === 'professional' || this.currentTenant?.tier === 'enterprise';
  }

  /**
   * Check if user has analytics access
   */
  hasAnalyticsAccess(): boolean {
    return this.authService.hasMinRole('analyst' as any);
  }

  /**
   * Check if user is admin
   */
  isAdmin(): boolean {
    return this.authService.hasMinRole('admin' as any);
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error = null;
  }

  /**
   * Get greeting based on time of day
   */
  getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  /**
   * Get tenant tier badge class
   */
  getTenantTierClass(): string {
    if (!this.currentTenant) return 'tier-free';
    return `tier-${this.currentTenant.tier}`;
  }
}