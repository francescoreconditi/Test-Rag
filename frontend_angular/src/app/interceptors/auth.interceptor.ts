/**
 * Authentication Interceptor
 * Automatically adds JWT token to API requests (Functional Interceptor for Angular 15+)
 */

import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';

export const authInterceptorFn: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  // Get token from localStorage
  const token = localStorage.getItem('rag_auth_token');

  // Add token to request if available
  let authReq = req;
  if (token && !req.url.includes('/auth/login') && !req.url.includes('/auth/refresh')) {
    authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
  }

  // Handle file uploads (don't set Content-Type for FormData)
  if (req.body instanceof FormData && authReq.headers.has('Content-Type')) {
    authReq = authReq.clone({
      headers: authReq.headers.delete('Content-Type')
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 Unauthorized errors
      if (error.status === 401 && !req.url.includes('/auth/')) {
        // Try to refresh token
        return authService.refreshToken().pipe(
          switchMap(() => {
            // Retry original request with new token
            const newToken = localStorage.getItem('rag_auth_token');
            const retryReq = req.clone({
              setHeaders: {
                Authorization: `Bearer ${newToken}`
              }
            });
            return next(retryReq);
          }),
          catchError(() => {
            // Refresh failed, logout user
            authService.logout();
            return throwError(() => error);
          })
        );
      }

      return throwError(() => error);
    })
  );
};

// Legacy class-based interceptor for backward compatibility
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Get token from localStorage
    const token = localStorage.getItem('rag_auth_token');

    // Add token to request if available
    let authReq = req;
    if (token && !req.url.includes('/auth/login') && !req.url.includes('/auth/refresh')) {
      authReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
    }

    // Handle file uploads (don't set Content-Type for FormData)
    if (req.body instanceof FormData && authReq.headers.has('Content-Type')) {
      authReq = authReq.clone({
        headers: authReq.headers.delete('Content-Type')
      });
    }

    return next.handle(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        // Handle 401 Unauthorized errors
        if (error.status === 401 && !req.url.includes('/auth/')) {
          // Try to refresh token
          return this.authService.refreshToken().pipe(
            switchMap(() => {
              // Retry original request with new token
              const newToken = localStorage.getItem('rag_auth_token');
              const retryReq = req.clone({
                setHeaders: {
                  Authorization: `Bearer ${newToken}`
                }
              });
              return next.handle(retryReq);
            }),
            catchError(() => {
              // Refresh failed, logout user
              this.authService.logout();
              return throwError(() => error);
            })
          );
        }

        return throwError(() => error);
      })
    );
  }
}