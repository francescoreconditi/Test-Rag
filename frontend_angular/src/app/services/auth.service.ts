/**
 * Authentication Service
 * Handles login, logout, session management, and multi-tenant authentication
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError, timer } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
// Alternative to jwt-decode
const jwtDecode = (token: string): any => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
};

import {
  AuthState,
  LoginRequest,
  LoginResponse,
  UserContext,
  TenantContext,
  UserRole,
  TenantTier
} from '../models/user-context';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly apiBaseUrl = 'http://localhost:8000';
  private readonly storageKeys = {
    token: 'rag_auth_token',
    refreshToken: 'rag_refresh_token',
    user: 'rag_user_context',
    tenant: 'rag_current_tenant'
  };

  private authStateSubject = new BehaviorSubject<AuthState>({
    isAuthenticated: false,
    user: null,
    tenants: [],
    currentTenant: null,
    loading: false,
    error: null
  });

  public authState$ = this.authStateSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.initializeAuth();
    this.startTokenRefreshTimer();
  }

  /**
   * Initialize authentication state from stored tokens
   */
  private initializeAuth(): void {
    const token = localStorage.getItem(this.storageKeys.token);
    const userJson = localStorage.getItem(this.storageKeys.user);
    const tenantJson = localStorage.getItem(this.storageKeys.tenant);

    if (token && userJson) {
      try {
        const user: UserContext = JSON.parse(userJson);
        const tenant: TenantContext | null = tenantJson ? JSON.parse(tenantJson) : null;

        // Verify token is not expired
        const decoded: any = jwtDecode(token);
        if (decoded.exp && decoded.exp > Date.now() / 1000) {
          this.updateAuthState({
            isAuthenticated: true,
            user,
            currentTenant: tenant,
            tenants: tenant ? [tenant] : [],
            loading: false,
            error: null
          });
        } else {
          this.clearStoredAuth();
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        this.clearStoredAuth();
      }
    }
  }

  /**
   * Login with email/password and optional tenant_id
   */
  login(loginRequest: LoginRequest): Observable<LoginResponse> {
    this.updateAuthState({ ...this.authStateSubject.value, loading: true, error: null });

    // MOCK LOGIN - Replace with real API call when backend is ready
    return new Observable<LoginResponse>(observer => {
      setTimeout(() => {
        // Mock user data based on email
        const mockUsers: { [key: string]: any } = {
          'admin@zcscompany.com': {
            user_id: '1',
            email: 'admin@zcscompany.com',
            role: UserRole.ADMIN,
            tenant_id: 'zcs',
            tenant_name: 'ZCS Company',
            tenant_tier: TenantTier.ENTERPRISE,
            permissions: ['users.manage', 'data.export', 'system.admin'],
            session_expires_at: new Date(Date.now() + 86400000)
          },
          'analyst@zcscompany.com': {
            user_id: '2',
            email: 'analyst@zcscompany.com',
            role: UserRole.ANALYST,
            tenant_id: 'zcs',
            tenant_name: 'ZCS Company',
            tenant_tier: TenantTier.ENTERPRISE,
            permissions: ['data.view', 'data.export'],
            session_expires_at: new Date(Date.now() + 86400000)
          },
          'viewer@zcscompany.com': {
            user_id: '3',
            email: 'viewer@zcscompany.com',
            role: UserRole.VIEWER,
            tenant_id: 'zcs',
            tenant_name: 'ZCS Company',
            tenant_tier: TenantTier.ENTERPRISE,
            permissions: ['data.view'],
            session_expires_at: new Date(Date.now() + 86400000)
          },
          'admin@example.com': {
            user_id: '4',
            email: 'admin@example.com',
            role: UserRole.ADMIN,
            tenant_id: 'example',
            tenant_name: 'Example Corp',
            tenant_tier: TenantTier.PROFESSIONAL,
            permissions: ['users.manage', 'data.export', 'system.admin'],
            session_expires_at: new Date(Date.now() + 86400000)
          }
        };

        const userData = mockUsers[loginRequest.email];
        console.log('Login attempt:', {
          email: loginRequest.email,
          password: loginRequest.password,
          userData: userData ? 'found' : 'not found'
        });

        if (userData && loginRequest.password === 'password123') {
          // Generate mock JWT token
          const mockToken = btoa(JSON.stringify({
            user_id: userData.user_id,
            email: userData.email,
            role: userData.role,
            tenant_id: userData.tenant_id,
            exp: Math.floor(Date.now() / 1000) + 86400 // 24 hours
          }));

          const response: LoginResponse = {
            success: true,
            token: mockToken,
            user: userData,
            tenants: [{
              tenant_id: userData.tenant_id,
              name: userData.tenant_name,
              tier: TenantTier.ENTERPRISE,
              features: ['analytics', 'export', 'multi-user'],
              user_count: 10,
              document_count: 1000
            }],
            message: 'Login successful'
          };

          observer.next(response);
          observer.complete();
        } else {
          observer.error({
            error: {
              message: 'Invalid email or password',
              code: 'AUTH_FAILED'
            }
          });
        }
      }, 500); // Simulate network delay
    }).pipe(
      map(response => this.mapLoginResponse(response)),
      tap(response => this.handleLoginSuccess(response)),
      catchError(error => this.handleLoginError(error))
    );
  }

  /**
   * Login with tenant selection (for users with multiple tenants)
   */
  loginWithTenant(email: string, password: string, tenantId: string): Observable<LoginResponse> {
    return this.login({ email, password, tenant_id: tenantId });
  }

  /**
   * Get available tenants for user
   */
  getUserTenants(email: string): Observable<TenantContext[]> {
    // MOCK TENANTS - Replace with real API call when backend is ready
    return new Observable<TenantContext[]>(observer => {
      setTimeout(() => {
        const mockTenants: TenantContext[] = [{
          tenant_id: 'zcs',
          name: 'ZCS Company',
          tier: TenantTier.ENTERPRISE,
          features: ['analytics', 'export', 'multi-user'],
          user_count: 10,
          document_count: 1000
        }];

        observer.next(mockTenants);
        observer.complete();
      }, 300);
    });
  }

  /**
   * Logout and clear session
   */
  logout(): void {
    const currentState = this.authStateSubject.value;

    // Call backend logout if authenticated
    if (currentState.isAuthenticated && currentState.user) {
      this.http.post(`${this.apiBaseUrl}/auth/logout`, {
        user_id: currentState.user.user_id,
        tenant_id: currentState.user.tenant_id
      }).pipe(
        catchError(error => {
          console.warn('Logout API call failed:', error);
          return throwError(() => error);
        })
      ).subscribe();
    }

    this.clearStoredAuth();
    this.updateAuthState({
      isAuthenticated: false,
      user: null,
      tenants: [],
      currentTenant: null,
      loading: false,
      error: null
    });

    this.router.navigate(['/login']);
  }

  /**
   * Switch to different tenant (for multi-tenant users)
   */
  switchTenant(tenantId: string): Observable<boolean> {
    const currentUser = this.authStateSubject.value.user;
    if (!currentUser) {
      return throwError(() => new Error('User not authenticated'));
    }

    return this.http.post<any>(`${this.apiBaseUrl}/auth/switch-tenant`, {
      user_id: currentUser.user_id,
      tenant_id: tenantId
    }).pipe(
      map(response => {
        if (response.success) {
          // Update user context with new tenant
          const updatedUser: UserContext = {
            ...currentUser,
            tenant_id: response.tenant.tenant_id,
            tenant_name: response.tenant.name,
            tenant_tier: response.tenant.tier
          };

          this.storeUserContext(updatedUser, response.tenant);
          this.updateAuthState({
            ...this.authStateSubject.value,
            user: updatedUser,
            currentTenant: response.tenant
          });
          return true;
        }
        return false;
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Refresh authentication token
   */
  refreshToken(): Observable<boolean> {
    const refreshToken = localStorage.getItem(this.storageKeys.refreshToken);
    if (!refreshToken) {
      this.logout();
      return throwError(() => new Error('No refresh token available'));
    }

    return this.http.post<any>(`${this.apiBaseUrl}/auth/refresh`, {
      refresh_token: refreshToken
    }).pipe(
      map(response => {
        if (response.token) {
          localStorage.setItem(this.storageKeys.token, response.token);
          return true;
        }
        return false;
      }),
      catchError(error => {
        this.logout();
        return throwError(() => error);
      })
    );
  }

  /**
   * Check if user has specific permission
   */
  hasPermission(permission: string): boolean {
    const user = this.authStateSubject.value.user;
    return user?.permissions.includes(permission) || false;
  }

  /**
   * Check if user has minimum role
   */
  hasMinRole(minRole: UserRole): boolean {
    const user = this.authStateSubject.value.user;
    if (!user) return false;

    const roleHierarchy: Record<UserRole, number> = {
      [UserRole.GUEST]: 0,
      [UserRole.VIEWER]: 1,
      [UserRole.ANALYST]: 2,
      [UserRole.ADMIN]: 3
    };

    return roleHierarchy[user.role] >= roleHierarchy[minRole];
  }

  /**
   * Get current user context
   */
  getCurrentUser(): UserContext | null {
    return this.authStateSubject.value.user;
  }

  /**
   * Get current tenant context
   */
  getCurrentTenant(): TenantContext | null {
    return this.authStateSubject.value.currentTenant;
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.authStateSubject.value.isAuthenticated;
  }

  // Private helper methods

  private mapLoginResponse(response: any): LoginResponse {
    if (response.success && response.user) {
      return {
        success: true,
        user: {
          ...response.user,
          session_expires_at: response.user.session_expires_at instanceof Date
            ? response.user.session_expires_at
            : new Date(response.user.session_expires_at),
          last_login: response.user.last_login ? new Date(response.user.last_login) : undefined
        },
        token: response.token,
        refresh_token: response.refresh_token,
        tenants: response.tenants,
        message: response.message
      };
    }

    return {
      success: false,
      error: response.error || 'Login failed',
      message: response.message
    };
  }

  private handleLoginSuccess(response: LoginResponse): void {
    if (response.success && response.user && response.token) {
      // Store tokens and user context
      localStorage.setItem(this.storageKeys.token, response.token);
      if (response.refresh_token) {
        localStorage.setItem(this.storageKeys.refreshToken, response.refresh_token);
      }

      // Get tenant info (simplified - in real app would call API)
      const tenant: TenantContext = {
        tenant_id: response.user.tenant_id,
        name: response.user.tenant_name,
        tier: response.user.tenant_tier,
        created_at: new Date(),
        is_active: true,
        max_users: 100,
        max_documents: 1000,
        features: ['basic', 'analytics']
      };

      this.storeUserContext(response.user, tenant);

      this.updateAuthState({
        isAuthenticated: true,
        user: response.user,
        currentTenant: tenant,
        tenants: [tenant],
        loading: false,
        error: null
      });

      this.router.navigate(['/dashboard']);
    }
  }

  private handleLoginError(error: any): Observable<LoginResponse> {
    const errorMessage = error.error?.message || error.message || 'Login failed';

    this.updateAuthState({
      ...this.authStateSubject.value,
      loading: false,
      error: errorMessage
    });

    return throwError(() => ({
      success: false,
      error: errorMessage,
      message: errorMessage
    }));
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    const errorMessage = error.error?.error || error.message || 'An error occurred';
    console.error('API Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }

  private storeUserContext(user: UserContext, tenant: TenantContext): void {
    localStorage.setItem(this.storageKeys.user, JSON.stringify(user));
    localStorage.setItem(this.storageKeys.tenant, JSON.stringify(tenant));
  }

  private clearStoredAuth(): void {
    Object.values(this.storageKeys).forEach(key => {
      localStorage.removeItem(key);
    });
  }

  private updateAuthState(newState: Partial<AuthState>): void {
    this.authStateSubject.next({
      ...this.authStateSubject.value,
      ...newState
    });
  }

  /**
   * Start automatic token refresh timer
   */
  private startTokenRefreshTimer(): void {
    timer(0, 300000).subscribe(() => { // Check every 5 minutes
      const token = localStorage.getItem(this.storageKeys.token);
      if (token) {
        try {
          const decoded: any = jwtDecode(token);
          const expiresIn = decoded.exp - (Date.now() / 1000);

          // Refresh if expires in less than 10 minutes
          if (expiresIn < 600 && expiresIn > 0) {
            this.refreshToken().subscribe();
          } else if (expiresIn <= 0) {
            this.logout();
          }
        } catch (error) {
          console.error('Token refresh error:', error);
        }
      }
    });
  }
}