import { Routes } from '@angular/router';
import { AuthGuard, AdminGuard, GuestGuard } from './guards/auth.guard';
import { LoginComponent } from './components/login/login.component';
import { UserRole } from './models/user-context';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full'
  },
  {
    path: 'login',
    component: LoginComponent,
    canActivate: [GuestGuard]
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./components/dashboard/dashboard.component').then(c => c.DashboardComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'analytics',
    loadComponent: () => import('./components/analytics/analytics.component').then(c => c.AnalyticsComponent),
    canActivate: [AuthGuard],
    data: { requiredRole: UserRole.ANALYST }
  },
  {
    path: 'documents',
    loadComponent: () => import('./components/documents/documents.component').then(c => c.DocumentsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'export',
    loadComponent: () => import('./components/export/export.component').then(c => c.ExportComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'security',
    loadComponent: () => import('./components/security/security.component').then(c => c.SecurityComponent),
    canActivate: [AdminGuard]
  },
  {
    path: 'unauthorized',
    loadComponent: () => import('./components/unauthorized/unauthorized.component').then(c => c.UnauthorizedComponent)
  },
  {
    path: '**',
    redirectTo: '/login'
  }
];
