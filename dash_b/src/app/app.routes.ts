import { Routes } from '@angular/router';
import { authGuard, loginGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full'
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component').then(m => m.LoginComponent),
    canActivate: [loginGuard]
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard]
  },
  {
    path: 'documents',
    loadComponent: () => import('./features/document-rag/document-rag.component').then(m => m.DocumentRagComponent),
    canActivate: [authGuard]
  },
  {
    path: 'csv-analysis',
    loadComponent: () => import('./features/csv-analysis/csv-analysis.component').then(m => m.CsvAnalysisComponent),
    canActivate: [authGuard]
  },
  {
    path: 'query',
    redirectTo: '/documents',
    pathMatch: 'full'
  },
  {
    path: 'faq',
    loadComponent: () => import('./features/faq-generation/faq-generation.component').then(m => m.FaqGenerationComponent),
    canActivate: [authGuard]
  },
  {
    path: 'enterprise',
    loadComponent: () => import('./features/enterprise/enterprise.component').then(m => m.EnterpriseComponent),
    canActivate: [authGuard]
  },
  {
    path: 'analytics',
    loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent),
    canActivate: [authGuard]
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent),
    canActivate: [authGuard]
  },
  {
    path: '**',
    redirectTo: '/login'
  }
];
