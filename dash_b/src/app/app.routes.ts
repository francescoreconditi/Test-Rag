import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'documents',
    loadComponent: () => import('./features/document-rag/document-rag.component').then(m => m.DocumentRagComponent)
  },
  {
    path: 'csv-analysis',
    loadComponent: () => import('./features/csv-analysis/csv-analysis.component').then(m => m.CsvAnalysisComponent)
  },
  {
    path: 'query',
    redirectTo: '/documents',
    pathMatch: 'full'
  },
  {
    path: 'faq',
    loadComponent: () => import('./features/faq-generation/faq-generation.component').then(m => m.FaqGenerationComponent)
  },
  {
    path: 'enterprise',
    loadComponent: () => import('./features/enterprise/enterprise.component').then(m => m.EnterpriseComponent)
  },
  {
    path: 'analytics',
    loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent)
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent)
  },
  {
    path: '**',
    redirectTo: '/dashboard'
  }
];
