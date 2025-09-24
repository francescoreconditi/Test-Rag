import { Injectable } from '@angular/core';
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  constructor(private authService: AuthService) {}

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Get the auth token from the auth service
    const authToken = this.authService.getAuthToken();
    const tokenType = localStorage.getItem('tokenType') || 'Bearer';

    // Clone the request and add the Authorization header if token exists
    if (authToken) {
      request = request.clone({
        setHeaders: {
          Authorization: `${tokenType} ${authToken}`
        }
      });
    }

    // Pass the request on to the next handler
    return next.handle(request);
  }
}