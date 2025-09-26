import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Subject, takeUntil } from 'rxjs';

import { FAQItem, FAQResponse } from '../../core/models/analysis.model';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { LoadingComponent } from '../../shared/components/loading/loading.component';

@Component({
  selector: 'app-faq-generation',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatInputModule,
    MatFormFieldModule,
    MatExpansionModule,
    MatDividerModule,
    MatChipsModule,
    MatProgressBarModule,
    MatSnackBarModule,
    LoadingComponent
  ],
  template: `
    <div class="faq-container">
      <div class="page-header">
        <h1><mat-icon class="title-icon">quiz</mat-icon> FAQ Intelligenti</h1>
        <p>Genera automaticamente FAQ dai tuoi documenti caricati</p>
      </div>

      <div class="content-grid">
        <!-- Generation Settings -->
        <mat-card class="settings-card">
          <mat-card-content>
            <form [formGroup]="settingsForm">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Numero di FAQ da generare</mat-label>
                <mat-select formControlName="numQuestions">
                  <mat-option [value]="5">5 FAQ (Veloce)</mat-option>
                  <mat-option [value]="10">10 FAQ (Standard)</mat-option>
                  <mat-option [value]="15">15 FAQ (Esteso)</mat-option>
                  <mat-option [value]="20">20 FAQ (Completo)</mat-option>
                </mat-select>
                <mat-hint>Più FAQ = analisi più approfondita ma più tempo</mat-hint>
              </mat-form-field>

              <div class="info-section">
                <mat-icon color="primary">info</mat-icon>
                <div class="info-text">
                  <strong>Come funziona:</strong>
                  <p>Il sistema analizza tutti i documenti caricati nel database e genera automaticamente le domande e risposte più rilevanti basandosi sul contenuto.</p>
                </div>
              </div>
            </form>
          </mat-card-content>
          <mat-card-actions>
            <button
              mat-raised-button
              color="primary"
              (click)="generateFAQs()"
              [disabled]="isGenerating">
              <mat-icon>auto_awesome</mat-icon>
              {{ isGenerating ? 'Generazione in corso...' : 'Genera FAQ' }}
            </button>
            <button
              mat-button
              (click)="clearResults()"
              [disabled]="isGenerating || !faqResponse">
              <mat-icon>clear</mat-icon>
              Cancella
            </button>
          </mat-card-actions>
        </mat-card>

        <!-- Statistics Card -->
        <mat-card class="stats-card" *ngIf="faqResponse">
          <mat-card-header>
            <div class="card-header-content">
              <h3 class="card-title"><mat-icon class="card-icon">analytics</mat-icon> Statistiche</h3>
            </div>
          </mat-card-header>
          <mat-card-content>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">{{ faqResponse.faqs.length }}</div>
                <div class="stat-label">FAQ Generate</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ getAverageConfidence() }}%</div>
                <div class="stat-label">Confidenza Media</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ faqResponse.processing_time | number:'1.1-1' }}s</div>
                <div class="stat-label">Tempo Elaborazione</div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Generated FAQs -->
      <div class="faqs-section" *ngIf="faqResponse && faqResponse.faqs.length > 0">
        <div class="section-header">
          <h2><mat-icon class="section-icon">help</mat-icon> FAQ Generate</h2>
          <div class="actions">
            <button mat-button (click)="exportToMarkdown()">
              <mat-icon>description</mat-icon>
              Esporta Markdown
            </button>
            <button mat-button (click)="exportToPDF()">
              <mat-icon>picture_as_pdf</mat-icon>
              Esporta PDF
            </button>
            <button mat-button (click)="copyAllToClipboard()">
              <mat-icon>content_copy</mat-icon>
              Copia Tutto
            </button>
          </div>
        </div>

        <mat-accordion class="faq-accordion">
          <mat-expansion-panel
            *ngFor="let faq of faqResponse.faqs; let i = index"
            [expanded]="expandedIndex === i">
            <mat-expansion-panel-header (click)="expandedIndex = i">
              <mat-panel-title>
                <span class="faq-number">Q{{ i + 1 }}</span>
                {{ faq.question }}
              </mat-panel-title>
              <mat-panel-description>
                <mat-chip class="confidence-chip" [class.high-confidence]="faq.confidence >= 0.8">
                  <mat-icon>psychology</mat-icon>
                  {{ (faq.confidence * 100) | number:'1.0-0' }}% confidenza
                </mat-chip>
              </mat-panel-description>
            </mat-expansion-panel-header>

            <div class="faq-content">
              <div class="answer-section">
                <h4>Risposta:</h4>
                <p>{{ faq.answer }}</p>
              </div>

              <mat-divider></mat-divider>

              <div class="faq-actions">
                <button mat-icon-button (click)="copyToClipboard(faq, i)" matTooltip="Copia FAQ">
                  <mat-icon>content_copy</mat-icon>
                </button>
                <button mat-icon-button (click)="editFAQ(faq, i)" matTooltip="Modifica FAQ">
                  <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button (click)="removeFAQ(i)" matTooltip="Rimuovi FAQ">
                  <mat-icon>delete</mat-icon>
                </button>
              </div>
            </div>
          </mat-expansion-panel>
        </mat-accordion>
      </div>

      <!-- Empty State -->
      <mat-card class="empty-state" *ngIf="!faqResponse && !isGenerating">
        <mat-card-content>
          <mat-icon class="empty-icon">quiz</mat-icon>
          <h3>Nessuna FAQ generata</h3>
          <p>Clicca su "Genera FAQ" per creare automaticamente domande e risposte dai tuoi documenti</p>
        </mat-card-content>
      </mat-card>

      <!-- Loading State -->
      <app-loading
        *ngIf="isGenerating"
        type="overlay"
        message="Generazione FAQ in corso...">
      </app-loading>
    </div>
  `,
  styles: [`
    .faq-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 32px;

      h1 {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 2rem;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #333;

        .title-icon {
          font-size: 2.2rem;
          width: 2.2rem;
          height: 2.2rem;
          color: #667eea;
        }
      }

      p {
        font-size: 1rem;
        color: #666;
        margin: 0;
      }
    }

    .content-grid {
      display: flex;
      flex-direction: column;
      gap: 24px;
      margin-bottom: 32px;
    }

    .settings-card {
      .card-header-content {
        padding: 8px 0;
        margin-bottom: 16px;

        .card-title {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 8px 0;
          font-size: 1.2rem;
          font-weight: 500;
          color: #333;
          line-height: 1.3;

          .card-icon {
            font-size: 1.4rem;
            width: 1.4rem;
            height: 1.4rem;
            color: #667eea;
          }
        }

        .card-subtitle {
          margin: 0;
          font-size: 0.9rem;
          color: #666;
          line-height: 1.4;
        }
      }

      .full-width {
        width: 100%;
      }

      .info-section {
        display: flex;
        gap: 12px;
        margin-top: 24px;
        padding: 16px;
        background: #f5f5f5;
        border-radius: 8px;

        mat-icon {
          flex-shrink: 0;
          margin-top: 2px;
        }

        .info-text {
          flex: 1;

          strong {
            display: block;
            margin-bottom: 8px;
            color: #333;
          }

          p {
            margin: 0;
            color: #666;
            font-size: 0.9rem;
            line-height: 1.5;
          }
        }
      }
    }

    .stats-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.2);

      .card-header-content {
        padding: 8px 0;
        margin-bottom: 16px;

        .card-title {
          color: white;
          margin: 0;
          font-size: 1.2rem;
          font-weight: 500;
          line-height: 1.3;
        }
      }

      .mat-mdc-card-header {
        color: white;
      }

      .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
      }

      .stat-item {
        text-align: center;
        padding: 16px 12px;
        background: rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);

        .stat-value {
          font-size: 1.6rem;
          font-weight: 600;
          margin-bottom: 6px;
          color: white;
        }

        .stat-label {
          font-size: 0.75rem;
          opacity: 0.95;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: rgba(255, 255, 255, 0.9);
        }
      }
    }

    .faqs-section {
      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;

        h2 {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 0;
          font-size: 1.5rem;
          font-weight: 500;
          color: #333;

          .section-icon {
            font-size: 1.6rem;
            width: 1.6rem;
            height: 1.6rem;
            color: #667eea;
          }
        }

        .actions {
          display: flex;
          gap: 8px;
        }
      }
    }

    .faq-accordion {
      border: 2px solid #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      mat-expansion-panel {
        box-shadow: none !important;
        border: none !important;
        background: white;

        &:not(:last-child) {
          border-bottom: 2px solid #e0e0e0 !important;
        }

        &:first-child {
          border-top: none;
        }

        &:last-child {
          border-bottom: none;
        }
      }

      ::ng-deep .mat-expansion-panel {
        box-shadow: none !important;
        border: none !important;
        margin: 0 !important;

        &:not(.mat-expanded) {
          .mat-expansion-panel-header {
            border-bottom: 2px solid #f5f5f5;
          }
        }

        .mat-expansion-panel-header {
          background: #fafafa;
          border: none;
          padding: 16px 20px;
          transition: all 0.3s ease;

          &:hover {
            background: #f0f0f0;
          }
        }

        .mat-expansion-panel-content {
          background: white;
          border-top: 1px solid #e0e0e0;
        }

        &.mat-expanded {
          .mat-expansion-panel-header {
            background: #e3f2fd;
            border-bottom: 2px solid #2196f3;
          }
        }
      }

      .faq-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background: #667eea;
        color: white;
        border-radius: 50%;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 12px;
      }

      .confidence-chip {
        background: #fff3cd;
        color: #856404;
        font-size: 0.75rem;
        border: 1px solid rgba(133, 100, 4, 0.3);

        &.high-confidence {
          background: #d4edda;
          color: #155724;
          border: 1px solid rgba(21, 87, 36, 0.3);
        }

        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
          margin-right: 4px;
        }
      }

      .faq-content {
        padding: 0 24px 16px 24px;

        .answer-section {
          margin-bottom: 16px;

          h4 {
            margin: 0 0 8px 0;
            color: #333;
            font-weight: 500;
          }

          p {
            margin: 0;
            color: #666;
            line-height: 1.6;
          }
        }

        .faq-actions {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }
      }
    }

    .empty-state {
      text-align: center;
      padding: 48px;

      .empty-icon {
        font-size: 64px;
        width: 64px;
        height: 64px;
        margin: 0 auto 16px;
        color: #ccc;
      }

      h3 {
        margin: 0 0 8px 0;
        color: #666;
      }

      p {
        margin: 0;
        color: #999;
      }
    }

    // Dark Theme Support
    ::ng-deep body.dark-theme {
      .page-header {
        h1 {
          color: rgba(255, 255, 255, 0.87) !important;

          .title-icon {
            color: #64b5f6 !important;
          }
        }

        p {
          color: rgba(255, 255, 255, 0.6) !important;
        }
      }

      .settings-card {
        background: #424242 !important;
        color: rgba(255, 255, 255, 0.87) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;

        .card-header-content {
          .card-title {
            color: rgba(255, 255, 255, 0.87) !important;

            .card-icon {
              color: #64b5f6 !important;
            }
          }

          .card-subtitle {
            color: rgba(255, 255, 255, 0.6) !important;
          }
        }

        .info-section {
          background: rgba(255, 255, 255, 0.05) !important;
          border: 1px solid rgba(255, 255, 255, 0.12) !important;

          .info-text {
            strong {
              color: rgba(255, 255, 255, 0.87) !important;
            }

            p {
              color: rgba(255, 255, 255, 0.6) !important;
            }
          }
        }
      }

      .stats-card {
        background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;

        .stat-item {
          background: rgba(255, 255, 255, 0.1) !important;
          border: 1px solid rgba(255, 255, 255, 0.15) !important;
        }
      }

      .section-header {
        h2 {
          color: rgba(255, 255, 255, 0.87) !important;

          .section-icon {
            color: #64b5f6 !important;
          }
        }
      }

      .faq-accordion {
        border: 2px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;

        mat-expansion-panel {
          background: #424242 !important;
          color: rgba(255, 255, 255, 0.87) !important;
          border-bottom-color: rgba(255, 255, 255, 0.2) !important;
        }

        ::ng-deep .mat-expansion-panel {
          .mat-expansion-panel-header {
            background: #525252 !important;
            color: rgba(255, 255, 255, 0.87) !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1) !important;

            &:hover {
              background: #616161 !important;
            }
          }

          .mat-expansion-panel-content {
            background: #424242 !important;
            border-top: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: rgba(255, 255, 255, 0.87) !important;
          }

          &.mat-expanded {
            .mat-expansion-panel-header {
              background: #1565c0 !important;
              border-bottom: 2px solid #42a5f5 !important;
            }
          }
        }

        .confidence-chip {
          background: rgba(255, 193, 7, 0.2) !important;
          color: #ffc107 !important;
          border: 1px solid rgba(255, 193, 7, 0.3) !important;

          &.high-confidence {
            background: rgba(76, 175, 80, 0.2) !important;
            color: #4caf50 !important;
            border: 1px solid rgba(76, 175, 80, 0.3) !important;
          }
        }

        .faq-content {
          .answer-section {
            h4 {
              color: rgba(255, 255, 255, 0.87) !important;
            }

            p {
              color: rgba(255, 255, 255, 0.7) !important;
            }
          }
        }
      }

      .empty-state {
        background: #424242 !important;
        color: rgba(255, 255, 255, 0.87) !important;

        .empty-icon {
          color: rgba(255, 255, 255, 0.3) !important;
        }

        h3 {
          color: rgba(255, 255, 255, 0.6) !important;
        }

        p {
          color: rgba(255, 255, 255, 0.4) !important;
        }
      }
    }

    // Light Mode fixes per mat-select
    ::ng-deep .mat-mdc-select-panel {
      background: white !important;
      border: 1px solid #e0e0e0 !important;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
    }

    ::ng-deep .mat-mdc-option {
      background: white !important;
      color: #333 !important;

      &:hover {
        background: #f5f5f5 !important;
      }

      &.mdc-list-item--selected {
        background: #e3f2fd !important;
        color: #1976d2 !important;
      }
    }

    ::ng-deep .mat-mdc-form-field {
      .mat-mdc-select-value-text {
        color: #333 !important;
      }

      .mat-mdc-select-arrow {
        color: #666 !important;
      }
    }

    @media (max-width: 768px) {
      .stats-grid {
        grid-template-columns: 1fr !important;
      }

      .section-header {
        flex-direction: column;
        align-items: flex-start !important;
        gap: 16px;

        .actions {
          width: 100%;
          flex-wrap: wrap;
        }
      }
    }
  `]
})
export class FaqGenerationComponent implements OnInit, OnDestroy {
  settingsForm: FormGroup;
  faqResponse: FAQResponse | null = null;
  isGenerating = false;
  expandedIndex = 0;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private notificationService: NotificationService,
    private snackBar: MatSnackBar
  ) {
    this.settingsForm = this.fb.group({
      numQuestions: [10, Validators.required]
    });
  }

  ngOnInit(): void {}

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  generateFAQs(): void {
    const numQuestions = this.settingsForm.value.numQuestions;
    this.isGenerating = true;

    this.apiService.generateFAQ(numQuestions)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.faqResponse = response;
          this.isGenerating = false;
          this.expandedIndex = 0;

          this.notificationService.showSuccess(
            'FAQ Generate',
            `Generate ${response.faqs.length} FAQ con successo!`
          );
        },
        error: (error) => {
          this.isGenerating = false;
          this.notificationService.showError(
            'Errore Generazione',
            error.message || 'Errore durante la generazione delle FAQ'
          );
        }
      });
  }

  clearResults(): void {
    this.faqResponse = null;
    this.expandedIndex = 0;
  }

  getAverageConfidence(): number {
    if (!this.faqResponse || !this.faqResponse.faqs.length) return 0;
    const total = this.faqResponse.faqs.reduce((sum, faq) => sum + faq.confidence, 0);
    return Math.round((total / this.faqResponse.faqs.length) * 100);
  }

  copyToClipboard(faq: FAQItem, index: number): void {
    const text = `Q${index + 1}: ${faq.question}\n\nA: ${faq.answer}`;
    navigator.clipboard.writeText(text).then(() => {
      this.snackBar.open('FAQ copiata negli appunti', 'Chiudi', { duration: 2000 });
    });
  }

  copyAllToClipboard(): void {
    if (!this.faqResponse) return;

    const text = this.faqResponse.faqs
      .map((faq, i) => `Q${i + 1}: ${faq.question}\n\nA: ${faq.answer}`)
      .join('\n\n---\n\n');

    navigator.clipboard.writeText(text).then(() => {
      this.snackBar.open('Tutte le FAQ copiate negli appunti', 'Chiudi', { duration: 2000 });
    });
  }

  exportToMarkdown(): void {
    if (!this.faqResponse) return;

    const markdown = `# FAQ - Domande Frequenti\n\n` +
      `_Generate automaticamente il ${new Date().toLocaleDateString('it-IT')}_\n\n` +
      this.faqResponse.faqs
        .map((faq, i) => `## Q${i + 1}: ${faq.question}\n\n${faq.answer}\n\n_Confidenza: ${Math.round(faq.confidence * 100)}%_`)
        .join('\n\n---\n\n');

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FAQ_${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    window.URL.revokeObjectURL(url);

    this.notificationService.showSuccess('Export', 'FAQ esportate in formato Markdown');
  }

  exportToPDF(): void {
    if (!this.faqResponse) return;

    this.apiService.exportToPDF(
      { faqs: this.faqResponse.faqs, timestamp: new Date().toISOString() },
      'faq'
    ).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const printWindow = window.open(url, '_blank');

        if (printWindow) {
          setTimeout(() => {
            printWindow.print();
          }, 1000);
        }

        setTimeout(() => {
          window.URL.revokeObjectURL(url);
        }, 5000);

        this.notificationService.showSuccess(
          'Export PDF',
          'Usa la finestra di stampa per salvare come PDF'
        );
      },
      error: (error) => {
        this.notificationService.showError(
          'Errore Export',
          'Errore durante l\'esportazione PDF'
        );
      }
    });
  }

  editFAQ(faq: FAQItem, index: number): void {
    this.notificationService.showInfo('Modifica', 'Funzionalità di modifica in sviluppo');
  }

  removeFAQ(index: number): void {
    if (!this.faqResponse) return;

    this.faqResponse.faqs.splice(index, 1);
    this.notificationService.showInfo('FAQ Rimossa', 'La FAQ è stata rimossa dalla lista');
  }
}