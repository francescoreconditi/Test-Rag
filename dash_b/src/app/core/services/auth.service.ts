import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface LoginRequest {
  tenant_id: string;
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  tenant_id: string;
  user_id: string;
  username: string;
  roles: string[];
}

export interface CurrentUser {
  tenant_id: string;
  user_id: string;
  username: string;
  roles: string[];
  authenticated: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly baseUrl = environment.apiUrl?.replace('/api/v1', '') || 'http://localhost:8000';
  private currentUserSubject = new BehaviorSubject<CurrentUser | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadCurrentUser();
  }

  login(tenantId: string, username: string, password: string): Observable<LoginResponse> {
    const loginRequest: LoginRequest = {
      tenant_id: tenantId,
      email: username, // API expects email field
      password: password
    };

    const headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });

    return this.http.post<LoginResponse>(`${this.baseUrl}/auth/login`, loginRequest, { headers })
      .pipe(
        map(response => {
          // Store authentication data
          localStorage.setItem('authToken', response.access_token);
          localStorage.setItem('tokenType', response.token_type);
          localStorage.setItem('expiresIn', response.expires_in.toString());
          localStorage.setItem('tenantId', response.tenant_id);

          // Set current user
          const user: CurrentUser = {
            tenant_id: response.tenant_id,
            user_id: response.user_id,
            username: response.username,
            roles: response.roles,
            authenticated: true
          };

          localStorage.setItem('currentUser', JSON.stringify(user));
          this.currentUserSubject.next(user);

          return response;
        }),
        catchError(error => {
          let errorMessage = 'Errore durante il login';

          if (error.status === 401) {
            errorMessage = 'Credenziali non valide';
          } else if (error.status === 404) {
            errorMessage = 'Tenant non trovato';
          } else if (error.status === 403) {
            errorMessage = 'Accesso negato';
          } else if (error.status === 500) {
            errorMessage = 'Errore del server';
          }

          return throwError(() => new Error(errorMessage));
        })
      );
  }

  logout(): void {
    // Clear all stored data
    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenType');
    localStorage.removeItem('expiresIn');
    localStorage.removeItem('tenantId');
    localStorage.removeItem('currentUser');

    // Clear current user
    this.currentUserSubject.next(null);
  }

  isAuthenticated(): boolean {
    const token = localStorage.getItem('authToken');
    const expiresIn = localStorage.getItem('expiresIn');

    if (!token || !expiresIn) {
      return false;
    }

    // Check if token is expired (simple check)
    const now = new Date().getTime() / 1000;
    const expiry = parseInt(expiresIn);

    if (now > expiry) {
      this.logout();
      return false;
    }

    return true;
  }

  getCurrentUser(): CurrentUser | null {
    return this.currentUserSubject.value;
  }

  getAuthToken(): string | null {
    return localStorage.getItem('authToken');
  }

  getTenantId(): string | null {
    return localStorage.getItem('tenantId');
  }

  hasRole(role: string): boolean {
    const user = this.getCurrentUser();
    return user?.roles?.includes(role) || false;
  }

  private loadCurrentUser(): void {
    const userJson = localStorage.getItem('currentUser');
    if (userJson && this.isAuthenticated()) {
      try {
        const user: CurrentUser = JSON.parse(userJson);
        this.currentUserSubject.next(user);
      } catch (error) {
        console.error('Error parsing stored user data:', error);
        this.logout();
      }
    }
  }

  // Mock login for demo purposes (when API is not available)
  mockLogin(tenantId: string, username: string, password: string): Observable<LoginResponse> {
    // Simulate API delay
    return new Observable(observer => {
      setTimeout(() => {
        // Check demo credentials
        const validCredentials = [
          { tenant: 'zcs-company', username: 'admin', password: 'admin123' },
          { tenant: 'demo-company', username: 'demo', password: 'demo123' },
          { tenant: 'test-tenant', username: 'test', password: 'test123' }
        ];

        const isValid = validCredentials.some(cred =>
          cred.tenant === tenantId &&
          cred.username === username &&
          cred.password === password
        );

        if (isValid) {
          const mockResponse: LoginResponse = {
            access_token: 'mock-jwt-token-' + Date.now(),
            token_type: 'Bearer',
            expires_in: Date.now() / 1000 + 3600, // 1 hour from now
            tenant_id: tenantId,
            user_id: `user-${username}-${tenantId}`,
            username: username,
            roles: username === 'admin' ? ['admin', 'user'] : ['user']
          };

          // Store authentication data
          localStorage.setItem('authToken', mockResponse.access_token);
          localStorage.setItem('tokenType', mockResponse.token_type);
          localStorage.setItem('expiresIn', mockResponse.expires_in.toString());
          localStorage.setItem('tenantId', mockResponse.tenant_id);

          // Set current user
          const user: CurrentUser = {
            tenant_id: mockResponse.tenant_id,
            user_id: mockResponse.user_id,
            username: mockResponse.username,
            roles: mockResponse.roles,
            authenticated: true
          };

          localStorage.setItem('currentUser', JSON.stringify(user));
          this.currentUserSubject.next(user);

          observer.next(mockResponse);
          observer.complete();
        } else {
          observer.error(new Error('Credenziali non valide'));
        }
      }, 1000); // 1 second delay to simulate network
    });
  }
}