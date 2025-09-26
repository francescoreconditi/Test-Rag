import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatGridListModule } from '@angular/material/grid-list';
import { RouterModule } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { IndexStats } from '../../core/models/analysis.model';

interface DashboardCard {
  title: string;
  description: string;
  icon: string;
  route: string;
  color: string;
  stats?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatGridListModule,
    RouterModule
  ],
  template: `
    <div class="dashboard-container">
      <div class="dashboard-header">
        <h1>🚀 RAG Dashboard</h1>
        <p>Sistema avanzato di Business Intelligence con AI e RAG</p>
      </div>

      <div class="stats-overview">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon">description</mat-icon>
              <div class="stat-details">
                <div class="stat-number">{{ indexStats.total_documents }}</div>
                <div class="stat-label">Documenti Indicizzati</div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon">storage</mat-icon>
              <div class="stat-details">
                <div class="stat-number">{{ formatVectorCount(indexStats.total_vectors) }}</div>
                <div class="stat-label">Vettori Generati</div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-content">
              <mat-icon class="stat-icon online">circle</mat-icon>
              <div class="stat-details">
                <div class="stat-number">Online</div>
                <div class="stat-label">Stato Sistema</div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <div class="feature-cards">
        <div class="card-grid">
          <mat-card
            *ngFor="let card of dashboardCards"
            class="feature-card"
            [class]="'card-' + card.color"
            [routerLink]="card.route">

            <mat-card-header>
              <div mat-card-avatar class="card-avatar">
                <mat-icon>{{ card.icon }}</mat-icon>
              </div>
              <mat-card-title>{{ card.title }}</mat-card-title>
              <mat-card-subtitle>{{ card.description }}</mat-card-subtitle>
            </mat-card-header>

            <mat-card-content>
              <div class="card-stats" *ngIf="card.stats">
                {{ card.stats }}
              </div>
            </mat-card-content>

            <mat-card-actions align="end">
              <button mat-button color="primary">
                <mat-icon>arrow_forward</mat-icon>
                Apri
              </button>
            </mat-card-actions>
          </mat-card>
        </div>
      </div>

      <div class="quick-actions">
        <mat-card class="actions-card">
          <mat-card-header>
            <mat-card-title>⚡ Azioni Rapide</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="actions-grid">
              <button mat-raised-button color="primary" routerLink="/documents">
                <mat-icon>upload</mat-icon>
                Carica Documenti
              </button>
              <button mat-raised-button color="accent" routerLink="/faq">
                <mat-icon>quiz</mat-icon>
                Genera FAQ
              </button>
              <button mat-raised-button routerLink="/enterprise">
                <mat-icon>business</mat-icon>
                Enterprise Mode
              </button>
              <button mat-raised-button routerLink="/analytics">
                <mat-icon>analytics</mat-icon>
                Visualizza Analytics
              </button>
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      padding: 24px;
      width: 100%;
      box-sizing: border-box;
    }

    .dashboard-header {
      text-align: center;
      margin-bottom: 32px;

      h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0 0 8px 0;
        background: linear-gradient(135deg, #3f51b5, #9c27b0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      p {
        font-size: 1.1rem;
        color: #666;
        margin: 0;
      }
    }

    .stats-overview {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 20px;
      margin-bottom: 32px;
      width: 100%;
    }

    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .stat-icon {
        font-size: 36px;
        width: 36px;
        height: 36px;
        color: #3f51b5;

        &.online {
          color: #4caf50;
        }
      }

      .stat-details {
        .stat-number {
          font-size: 1.8rem;
          font-weight: 700;
          color: #333;
        }

        .stat-label {
          font-size: 0.9rem;
          color: #666;
        }
      }
    }

    .feature-cards {
      margin-bottom: 32px;
    }

    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
      width: 100%;
    }

    .feature-card {
      cursor: pointer;
      transition: all 0.3s ease;
      border-left: 4px solid transparent;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
      }

      &.card-primary {
        border-left-color: #3f51b5;
      }

      &.card-accent {
        border-left-color: #e91e63;
      }

      &.card-warn {
        border-left-color: #ff9800;
      }

      &.card-success {
        border-left-color: #4caf50;
      }

      .card-avatar {
        background: linear-gradient(135deg, #3f51b5, #9c27b0);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;

        mat-icon {
          font-size: 24px;
          width: 24px;
          height: 24px;
        }
      }

      .card-stats {
        font-size: 0.9rem;
        color: #666;
        margin-top: 8px;
      }
    }

    .quick-actions {
      .actions-card {
        .actions-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;

          button {
            height: 48px;
            font-weight: 500;

            mat-icon {
              margin-right: 8px;
            }
          }
        }
      }
    }

    @media (max-width: 768px) {
      .dashboard-container {
        padding: 16px;
      }

      .dashboard-header h1 {
        font-size: 2rem;
      }

      .card-grid {
        grid-template-columns: 1fr;
      }

      .stats-overview {
        grid-template-columns: 1fr;
      }

      .actions-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class DashboardComponent implements OnInit {
  indexStats: IndexStats = { total_documents: 0, total_vectors: 0 };

  dashboardCards: DashboardCard[] = [
    {
      title: 'Gestione Documenti',
      description: 'Carica e analizza documenti PDF, Word, Excel e altri formati',
      icon: 'folder',
      route: '/documents',
      color: 'primary',
      stats: 'Supporta 10+ formati file'
    },
    {
      title: 'Analisi CSV',
      description: 'Analisi avanzata di dati finanziari e business intelligence',
      icon: 'table_chart',
      route: '/csv-analysis',
      color: 'accent',
      stats: 'AI-powered insights'
    },
    {
      title: 'FAQ Intelligenti',
      description: 'Genera automaticamente FAQ dai tuoi documenti',
      icon: 'quiz',
      route: '/faq',
      color: 'warn',
      stats: 'Come Google NotebookLM'
    },
    {
      title: 'Enterprise Mode',
      description: 'Funzionalità avanzate per uso aziendale',
      icon: 'business',
      route: '/enterprise',
      color: 'success',
      stats: 'Hybrid retrieval & ontology'
    }
  ];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadStats();
  }

  private loadStats(): void {
    this.apiService.getIndexStats().subscribe({
      next: (stats) => {
        this.indexStats = stats;
      },
      error: (error) => {
        console.warn('Failed to load stats:', error);
      }
    });
  }

  formatVectorCount(count: number): string {
    if (count < 1000) return count.toString();
    if (count < 1000000) return `${(count / 1000).toFixed(1)}K`;
    return `${(count / 1000000).toFixed(1)}M`;
  }
}