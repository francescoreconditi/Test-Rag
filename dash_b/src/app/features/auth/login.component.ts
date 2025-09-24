import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatSnackBarModule
  ],
  template: `
    <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px;">
      <div style="width: 100%; max-width: 400px; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">

        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #667eea; margin: 0; font-size: 28px;">🚀 RAG Dashboard</h1>
          <p style="color: #666; margin: 10px 0 0 0; font-size: 14px;">Sistema avanzato di Business Intelligence</p>
        </div>

        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">

          <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #333;">Username</label>
            <input type="text" formControlName="username" required
                   style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; box-sizing: border-box;">
          </div>

          <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #333;">Password</label>
            <input type="password" formControlName="password" required
                   style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; box-sizing: border-box;">
          </div>

          <div style="margin-bottom: 30px;">
            <label style="display: block; margin-bottom: 5px; font-weight: 500; color: #333;">Tenant ID (opzionale)</label>
            <select formControlName="tenantId"
                    style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; background: white;">
              <option value="">Default</option>
              <option value="zcs-company">ZCS Company</option>
              <option value="demo-company">Demo Company</option>
              <option value="test-tenant">Test Tenant</option>
            </select>
          </div>

          <button type="button" [disabled]="loginForm.invalid || isLogging" (click)="onSubmit()"
                  style="width: 100%; height: 48px; font-size: 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
            <span *ngIf="!isLogging">Accedi</span>
            <span *ngIf="isLogging">Accesso in corso...</span>
          </button>


        </form>

        <div style="margin-top: 20px; text-align: center;">
          <button type="button" (click)="showDemoCredentials = !showDemoCredentials"
                  style="background: none; border: none; color: #667eea; cursor: pointer; text-decoration: underline;">
            {{ showDemoCredentials ? 'Nascondi' : 'Mostra' }} Credenziali Demo
          </button>
        </div>

        <div *ngIf="showDemoCredentials" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
          <h4 style="margin: 0 0 10px 0; font-size: 14px; color: #666;">Credenziali Demo:</h4>
          <div *ngFor="let demo of demoCredentials"
               (click)="setDemoCredentials(demo)"
               style="cursor: pointer; padding: 8px; margin: 4px 0; background: white; border-radius: 4px; border: 1px solid #e0e0e0; font-size: 12px;">
            <strong>{{ demo.tenant }}</strong>: {{ demo.username }} / {{ demo.password }}
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    /* Login page styles are now inline for better compatibility */
  `]
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  hidePassword = true;
  isLogging = false;
  isDarkMode = false;
  showDemoCredentials = false;

  availableTenants = [
    {
      id: 'zcs-company',
      name: 'ZCS Company',
      description: 'Tenant principale per ZCS Company'
    },
    {
      id: 'demo-company',
      name: 'Demo Company',
      description: 'Tenant di dimostrazione'
    },
    {
      id: 'test-tenant',
      name: 'Test Tenant',
      description: 'Tenant per testing'
    }
  ];

  demoCredentials = [
    { tenant: 'zcs-company', username: 'admin', password: 'admin123' },
    { tenant: 'demo-company', username: 'demo', password: 'demo123' },
    { tenant: 'test-tenant', username: 'test', password: 'test123' }
  ];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService,
    private themeService: ThemeService,
    private snackBar: MatSnackBar
  ) {
    this.loginForm = this.fb.group({
      tenantId: [''],  // Optional field
      username: ['', Validators.required],
      password: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    // Check if already logged in
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/dashboard']);
      return;
    }

    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.isDarkMode = theme.isDark;
    });

    // Set default demo credentials
    this.setDemoCredentials(this.demoCredentials[0]);
  }


  onSubmit(): void {
    if (this.loginForm.valid) {
      const formValue = this.loginForm.value;
      this.isLogging = true;

      this.authService.mockLogin(formValue.tenantId, formValue.username, formValue.password)
        .subscribe({
          next: (response) => {
            this.isLogging = false;
            this.snackBar.open('Login effettuato con successo!', 'Chiudi', {
              duration: 3000,
              panelClass: ['success-snack']
            });

            setTimeout(() => {
              this.router.navigate(['/dashboard']).then(
                (success) => {
                  if (!success) {
                    window.location.href = '/dashboard';
                  }
                },
                (error) => {
                  window.location.href = '/dashboard';
                }
              );
            }, 100);
          },
          error: (error) => {
            this.isLogging = false;
            this.snackBar.open(
              error.message || 'Credenziali non valide',
              'Chiudi',
              {
                duration: 5000,
                panelClass: ['error-snack']
              }
            );
          }
        });
    }
  }

  setDemoCredentials(demo: any): void {
    this.loginForm.patchValue({
      tenantId: demo.tenant,
      username: demo.username,
      password: demo.password
    });
  }

  toggleTheme(): void {
    this.themeService.toggleDarkMode();
  }
}