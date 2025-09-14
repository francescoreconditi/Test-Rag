/**
 * Security Dashboard Component (Admin Only)
 * Manage users, roles, security settings, and audit logs
 */

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { UserRole, TenantTier, SecurityEvent } from '../../models/user-context';

interface User {
  id: string;
  email: string;
  role: UserRole;
  tenant_id: string;
  tenant_name: string;
  is_active: boolean;
  last_login?: Date;
  created_at: Date;
  login_attempts: number;
}

interface SecurityMetrics {
  totalUsers: number;
  activeUsers: number;
  failedLogins24h: number;
  securityEvents24h: number;
  topTenants: { name: string; userCount: number }[];
}

interface AuditLog {
  id: string;
  timestamp: Date;
  user_id: string;
  user_email: string;
  action: string;
  resource: string;
  ip_address: string;
  status: 'success' | 'failed';
  details: any;
}

@Component({
  selector: 'app-security',
  templateUrl: './security.component.html',
  styleUrls: ['./security.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule]
})
export class SecurityComponent implements OnInit, OnDestroy {
  users: User[] = [];
  securityMetrics: SecurityMetrics | null = null;
  auditLogs: AuditLog[] = [];
  securityEvents: SecurityEvent[] = [];

  isLoading = false;
  error: string | null = null;

  // Filters
  userFilter = '';
  roleFilter: UserRole | 'all' = 'all';
  statusFilter: 'all' | 'active' | 'inactive' = 'all';

  // User management
  selectedUser: User | null = null;
  showUserModal = false;
  editingUser: Partial<User> = {};

  // Security settings
  securitySettings = {
    passwordMinLength: 8,
    requireMfa: false,
    sessionTimeoutMinutes: 60,
    maxLoginAttempts: 3,
    lockoutDurationMinutes: 30
  };

  // For audit log details expansion
  showDetails: string | null = null;

  private subscriptions = new Subscription();

  // Available roles for dropdown
  readonly userRoles = Object.values(UserRole);

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    this.loadSecurityData();
    this.loadUsers();
    this.loadAuditLogs();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  /**
   * Load security dashboard data
   */
  private loadSecurityData(): void {
    this.isLoading = true;

    // Mock security metrics
    setTimeout(() => {
      this.securityMetrics = {
        totalUsers: 127,
        activeUsers: 89,
        failedLogins24h: 15,
        securityEvents24h: 8,
        topTenants: [
          { name: 'ZCS Company', userCount: 45 },
          { name: 'Tech Corp', userCount: 32 },
          { name: 'Data Solutions', userCount: 28 },
          { name: 'Finance Group', userCount: 22 }
        ]
      };

      // Mock security events
      this.securityEvents = [
        {
          event_type: 'Failed Login',
          user_id: 'user_123',
          tenant_id: 'tenant_1',
          details: { attempts: 3, ip: '192.168.1.100' },
          timestamp: new Date(Date.now() - 3600000),
          ip_address: '192.168.1.100'
        },
        {
          event_type: 'Account Locked',
          user_id: 'user_456',
          tenant_id: 'tenant_2',
          details: { reason: 'Too many failed attempts' },
          timestamp: new Date(Date.now() - 7200000),
          ip_address: '192.168.1.200'
        }
      ];

      this.isLoading = false;
    }, 1000);
  }

  /**
   * Load users list
   */
  private loadUsers(): void {
    // Mock users data
    this.users = [
      {
        id: 'user_1',
        email: 'admin@zcscompany.com',
        role: UserRole.ADMIN,
        tenant_id: 'tenant_1',
        tenant_name: 'ZCS Company',
        is_active: true,
        last_login: new Date(Date.now() - 3600000),
        created_at: new Date(Date.now() - 86400000 * 30),
        login_attempts: 0
      },
      {
        id: 'user_2',
        email: 'analyst@techcorp.com',
        role: UserRole.ANALYST,
        tenant_id: 'tenant_2',
        tenant_name: 'Tech Corp',
        is_active: true,
        last_login: new Date(Date.now() - 7200000),
        created_at: new Date(Date.now() - 86400000 * 15),
        login_attempts: 0
      },
      {
        id: 'user_3',
        email: 'viewer@datasolutions.com',
        role: UserRole.VIEWER,
        tenant_id: 'tenant_3',
        tenant_name: 'Data Solutions',
        is_active: false,
        last_login: new Date(Date.now() - 86400000 * 7),
        created_at: new Date(Date.now() - 86400000 * 60),
        login_attempts: 2
      }
    ];
  }

  /**
   * Load audit logs
   */
  private loadAuditLogs(): void {
    // Mock audit logs
    this.auditLogs = [
      {
        id: 'audit_1',
        timestamp: new Date(Date.now() - 3600000),
        user_id: 'user_1',
        user_email: 'admin@zcscompany.com',
        action: 'LOGIN',
        resource: 'AUTH',
        ip_address: '192.168.1.50',
        status: 'success',
        details: { session_duration: 3600 }
      },
      {
        id: 'audit_2',
        timestamp: new Date(Date.now() - 7200000),
        user_id: 'user_2',
        user_email: 'analyst@techcorp.com',
        action: 'DOCUMENT_UPLOAD',
        resource: 'DOCUMENTS',
        ip_address: '192.168.1.75',
        status: 'success',
        details: { document_count: 3 }
      },
      {
        id: 'audit_3',
        timestamp: new Date(Date.now() - 10800000),
        user_id: 'user_3',
        user_email: 'viewer@datasolutions.com',
        action: 'FAILED_LOGIN',
        resource: 'AUTH',
        ip_address: '192.168.1.200',
        status: 'failed',
        details: { reason: 'Invalid password' }
      }
    ];
  }

  /**
   * Get filtered users
   */
  getFilteredUsers(): User[] {
    let filtered = this.users;

    // Filter by search term
    if (this.userFilter) {
      const term = this.userFilter.toLowerCase();
      filtered = filtered.filter(user =>
        user.email.toLowerCase().includes(term) ||
        user.tenant_name.toLowerCase().includes(term)
      );
    }

    // Filter by role
    if (this.roleFilter !== 'all') {
      filtered = filtered.filter(user => user.role === this.roleFilter);
    }

    // Filter by status
    if (this.statusFilter !== 'all') {
      const isActive = this.statusFilter === 'active';
      filtered = filtered.filter(user => user.is_active === isActive);
    }

    return filtered;
  }

  /**
   * Open user modal for editing
   */
  editUser(user: User): void {
    this.selectedUser = user;
    this.editingUser = { ...user };
    this.showUserModal = true;
  }

  /**
   * Open user modal for creating new user
   */
  createUser(): void {
    this.selectedUser = null;
    this.editingUser = {
      email: '',
      role: UserRole.VIEWER,
      is_active: true
    };
    this.showUserModal = true;
  }

  /**
   * Save user changes
   */
  saveUser(): void {
    if (this.selectedUser) {
      // Update existing user
      const index = this.users.findIndex(u => u.id === this.selectedUser!.id);
      if (index !== -1) {
        this.users[index] = { ...this.users[index], ...this.editingUser };
      }
    } else {
      // Create new user
      const newUser: User = {
        id: 'user_' + Date.now(),
        email: this.editingUser.email!,
        role: this.editingUser.role!,
        tenant_id: 'tenant_1', // Default tenant
        tenant_name: 'Default Tenant',
        is_active: this.editingUser.is_active!,
        created_at: new Date(),
        login_attempts: 0
      };
      this.users.unshift(newUser);
    }

    this.closeUserModal();
  }

  /**
   * Delete user
   */
  deleteUser(user: User): void {
    if (confirm(`Are you sure you want to delete user "${user.email}"?`)) {
      this.users = this.users.filter(u => u.id !== user.id);
    }
  }

  /**
   * Toggle user active status
   */
  toggleUserStatus(user: User): void {
    const index = this.users.findIndex(u => u.id === user.id);
    if (index !== -1) {
      this.users[index].is_active = !this.users[index].is_active;
    }
  }

  /**
   * Reset user login attempts
   */
  resetLoginAttempts(user: User): void {
    const index = this.users.findIndex(u => u.id === user.id);
    if (index !== -1) {
      this.users[index].login_attempts = 0;
    }
  }

  /**
   * Close user modal
   */
  closeUserModal(): void {
    this.showUserModal = false;
    this.selectedUser = null;
    this.editingUser = {};
  }

  /**
   * Get user status icon
   */
  getUserStatusIcon(user: User): string {
    if (!user.is_active) return '❌';
    if (user.login_attempts >= 3) return '🔒';
    return '✅';
  }

  /**
   * Get role badge class
   */
  getRoleBadgeClass(role: UserRole): string {
    switch (role) {
      case UserRole.ADMIN: return 'role-admin';
      case UserRole.ANALYST: return 'role-analyst';
      case UserRole.VIEWER: return 'role-viewer';
      case UserRole.GUEST: return 'role-guest';
      default: return 'role-guest';
    }
  }

  /**
   * Get audit action icon
   */
  getAuditActionIcon(action: string): string {
    switch (action.toUpperCase()) {
      case 'LOGIN': return '🔐';
      case 'LOGOUT': return '🚪';
      case 'DOCUMENT_UPLOAD': return '📤';
      case 'DOCUMENT_DELETE': return '🗑️';
      case 'QUERY': return '🔍';
      case 'EXPORT': return '📊';
      case 'FAILED_LOGIN': return '❌';
      default: return '📝';
    }
  }

  /**
   * Get audit status class
   */
  getAuditStatusClass(status: string): string {
    return status === 'success' ? 'status-success' : 'status-failed';
  }

  /**
   * Format time ago
   */
  formatTimeAgo(date: Date): string {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMinutes < 60) {
      return `${diffMinutes}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return `${diffDays}d ago`;
    }
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.error = null;
  }

  /**
   * Export audit logs
   */
  exportAuditLogs(): void {
    const csv = this.convertToCSV(this.auditLogs);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * Convert array to CSV
   */
  private convertToCSV(data: any[]): string {
    if (!data.length) return '';

    const headers = Object.keys(data[0]).join(',');
    const rows = data.map(row =>
      Object.values(row).map(value =>
        typeof value === 'object' ? JSON.stringify(value) : String(value)
      ).join(',')
    );

    return [headers, ...rows].join('\n');
  }
}