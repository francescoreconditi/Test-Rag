/**
 * Login Component
 * Multi-tenant authentication with tenant selection
 */

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { TenantContext, UserRole } from '../../models/user-context';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule]
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  isLoading = false;
  errorMessage = '';
  availableTenants: TenantContext[] = [];
  showTenantSelection = false;
  selectedTenant: TenantContext | null = null;

  // Demo credentials for testing
  demoCredentials = [
    { email: 'admin@zcscompany.com', password: 'admin123', role: 'Admin' },
    { email: 'analyst@zcscompany.com', password: 'analyst123', role: 'Analyst' },
    { email: 'viewer@zcscompany.com', password: 'viewer123', role: 'Viewer' }
  ];

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      tenant_id: ['']
    });
  }

  ngOnInit(): void {
    // Check if already authenticated
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/dashboard']);
    }

    // Subscribe to auth state for error handling
    this.authService.authState$.subscribe(state => {
      this.isLoading = state.loading;
      this.errorMessage = state.error || '';
    });
  }

  /**
   * Handle login form submission
   */
  onSubmit(): void {
    if (this.loginForm.valid) {
      const formValue = this.loginForm.value;

      // If tenant is selected, login with tenant
      if (this.selectedTenant) {
        this.loginWithTenant(formValue.email, formValue.password, this.selectedTenant.tenant_id);
      } else {
        this.login(formValue.email, formValue.password);
      }
    } else {
      this.markFormGroupTouched();
    }
  }

  /**
   * Login without tenant (will get tenants if multiple available)
   */
  private login(email: string, password: string): void {
    this.errorMessage = '';

    this.authService.login({ email, password }).subscribe({
      next: (response) => {
        if (response.success) {
          // Login successful - already handled in service
          console.log('Login successful');
        } else if (response.error?.includes('multiple tenants')) {
          // User has multiple tenants - show tenant selection
          this.loadUserTenants(email);
        }
      },
      error: (error) => {
        console.error('Login failed:', error);
      }
    });
  }

  /**
   * Login with specific tenant
   */
  private loginWithTenant(email: string, password: string, tenantId: string): void {
    this.authService.loginWithTenant(email, password, tenantId).subscribe({
      next: (response) => {
        if (response.success) {
          console.log('Login with tenant successful');
        }
      },
      error: (error) => {
        console.error('Login with tenant failed:', error);
      }
    });
  }

  /**
   * Load available tenants for user
   */
  private loadUserTenants(email: string): void {
    this.authService.getUserTenants(email).subscribe({
      next: (tenants) => {
        this.availableTenants = tenants;
        this.showTenantSelection = true;
      },
      error: (error) => {
        this.errorMessage = 'Failed to load tenants: ' + error.message;
      }
    });
  }

  /**
   * Select tenant and proceed with login
   */
  selectTenant(tenant: TenantContext): void {
    this.selectedTenant = tenant;
    this.showTenantSelection = false;

    const formValue = this.loginForm.value;
    this.loginWithTenant(formValue.email, formValue.password, tenant.tenant_id);
  }

  /**
   * Go back to regular login
   */
  goBackToLogin(): void {
    this.showTenantSelection = false;
    this.selectedTenant = null;
    this.availableTenants = [];
  }

  /**
   * Fill form with demo credentials
   */
  useDemoCredentials(demo: any): void {
    this.loginForm.patchValue({
      email: demo.email,
      password: demo.password
    });
  }

  /**
   * Clear error message
   */
  clearError(): void {
    this.errorMessage = '';
  }

  /**
   * Mark all form controls as touched to show validation errors
   */
  private markFormGroupTouched(): void {
    Object.keys(this.loginForm.controls).forEach(key => {
      this.loginForm.get(key)?.markAsTouched();
    });
  }

  /**
   * Get form control error message
   */
  getErrorMessage(controlName: string): string {
    const control = this.loginForm.get(controlName);
    if (control?.errors && control.touched) {
      if (control.errors['required']) {
        return `${controlName.charAt(0).toUpperCase() + controlName.slice(1)} is required`;
      }
      if (control.errors['email']) {
        return 'Please enter a valid email';
      }
      if (control.errors['minlength']) {
        return `${controlName.charAt(0).toUpperCase() + controlName.slice(1)} must be at least 6 characters`;
      }
    }
    return '';
  }

  /**
   * Check if form control has error
   */
  hasError(controlName: string): boolean {
    const control = this.loginForm.get(controlName);
    return !!(control?.errors && control.touched);
  }
}