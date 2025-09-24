import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBarModule, MatSnackBar } from '@angular/material/snack-bar';
import { Subject, takeUntil } from 'rxjs';

import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { FileUploadComponent } from '../../shared/components/file-upload/file-upload.component';
import { DocumentAnalysis, IndexStats, QueryRequest, QueryResponse } from '../../core/models/analysis.model';
import { FileUploadProgress } from '../../core/models/ui.model';

@Component({
  selector: 'app-document-rag',
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
    MatChipsModule,
    MatExpansionModule,
    MatTabsModule,
    MatDividerModule,
    MatSnackBarModule,
    LoadingComponent,
    FileUploadComponent
  ],
  template: `
    <div class="document-rag-container">
      <div class="page-header">
        <h1>📚 Gestione Documenti RAG</h1>
        <p>Carica e analizza documenti per il sistema RAG</p>
      </div>

      <div class="content-tabs">
        <mat-tab-group [(selectedIndex)]="selectedTabIndex">
          <!-- Upload Tab -->
          <mat-tab label="Carica Documenti">
            <div class="tab-content">
              <div class="upload-section">
                <app-file-upload
                  title="Carica Documenti per RAG"
                  subtitle="Supporta PDF, Word, Excel, CSV, immagini e altri formati"
                  [multiple]="true"
                  (filesSelected)="onFilesSelected($event)"
                  (uploadCompleted)="onUploadCompleted($event)">
                </app-file-upload>

                <!-- Analysis Type Selection -->
                <mat-card *ngIf="selectedFiles.length > 0" class="analysis-config-card">
                  <mat-card-header>
                    <mat-card-title>Configurazione Analisi</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <form [formGroup]="analysisForm" class="analysis-form">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Tipo di Analisi</mat-label>
                        <mat-select formControlName="analysisType">
                          <mat-option value="automatic">Automatico (raccomandato)</mat-option>
                          <mat-option value="bilancio">Bilancio - Analisi finanziaria</mat-option>
                          <mat-option value="fatturato">Fatturato - Analisi vendite</mat-option>
                          <mat-option value="magazzino">Magazzino - Gestione scorte</mat-option>
                          <mat-option value="contratto">Contratto - Analisi legale</mat-option>
                          <mat-option value="presentazione">Presentazione - Slide deck</mat-option>
                          <mat-option value="generale">Generale - Analisi generica</mat-option>
                        </mat-select>
                      </mat-form-field>

                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Note aggiuntive (opzionale)</mat-label>
                        <textarea
                          matInput
                          formControlName="notes"
                          placeholder="Inserisci eventuali note o istruzioni specifiche per l'analisi..."
                          rows="3">
                        </textarea>
                      </mat-form-field>
                    </form>
                  </mat-card-content>
                  <mat-card-actions>
                    <button
                      mat-raised-button
                      color="primary"
                      (click)="startAnalysis()"
                      [disabled]="isAnalyzing || selectedFiles.length === 0">
                      <mat-icon>analytics</mat-icon>
                      Avvia Analisi ({{ selectedFiles.length }} file)
                    </button>
                  </mat-card-actions>
                </mat-card>
              </div>
            </div>
          </mat-tab>

          <!-- Query Tab -->
          <mat-tab label="Query RAG">
            <div class="tab-content">
              <div class="query-section">
                <mat-card class="query-card">
                  <mat-card-header>
                    <mat-card-title>🔍 Interroga i Documenti</mat-card-title>
                    <mat-card-subtitle>
                      {{ indexStats.total_documents }} documenti indicizzati,
                      {{ formatVectorCount(indexStats.total_vectors) }} vettori
                    </mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <form [formGroup]="queryForm" class="query-form">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Inserisci la tua domanda</mat-label>
                        <textarea
                          matInput
                          formControlName="query"
                          placeholder="Es: Qual è l'EBITDA dell'azienda negli ultimi tre anni?"
                          rows="3">
                        </textarea>
                        <mat-hint>Poni domande specifiche sui tuoi documenti caricati</mat-hint>
                      </mat-form-field>

                      <div class="query-options">
                        <mat-form-field appearance="outline">
                          <mat-label>Formato Output</mat-label>
                          <mat-select formControlName="outputFormat">
                            <mat-option value="json">JSON Strutturato</mat-option>
                            <mat-option value="text">Testo Semplice</mat-option>
                            <mat-option value="pdf">Report PDF</mat-option>
                          </mat-select>
                        </mat-form-field>

                        <mat-form-field appearance="outline">
                          <mat-label>Risultati Max</mat-label>
                          <mat-select formControlName="maxResults">
                            <mat-option value="3">3 (Veloce)</mat-option>
                            <mat-option value="5">5 (Standard)</mat-option>
                            <mat-option value="10">10 (Dettagliato)</mat-option>
                          </mat-select>
                        </mat-form-field>
                      </div>
                    </form>
                  </mat-card-content>
                  <mat-card-actions>
                    <button
                      mat-raised-button
                      color="primary"
                      (click)="executeQuery()"
                      [disabled]="isQuerying || !queryForm.valid || indexStats.total_documents === 0">
                      <mat-icon>search</mat-icon>
                      Cerca Risposta
                    </button>
                    <button
                      mat-button
                      (click)="clearQuery()"
                      [disabled]="isQuerying">
                      <mat-icon>clear</mat-icon>
                      Cancella
                    </button>
                  </mat-card-actions>
                </mat-card>

                <!-- Query Results -->
                <mat-card *ngIf="queryResult" class="results-card">
                  <mat-card-header>
                    <mat-card-title>📋 Risultato Query</mat-card-title>
                    <mat-card-subtitle>
                      Confidenza: {{ (queryResult.confidence * 100) | number:'1.1-1' }}% •
                      Tempo: {{ queryResult.processing_time | number:'1.2-2' }}s
                    </mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="query-response">
                      <p>{{ queryResult.response }}</p>
                    </div>

                    <mat-divider></mat-divider>

                    <div class="sources-section" *ngIf="queryResult.sources.length > 0">
                      <h4>📚 Fonti ({{ queryResult.sources.length }})</h4>
                      <mat-expansion-panel *ngFor="let source of queryResult.sources; let i = index">
                        <mat-expansion-panel-header>
                          <mat-panel-title>
                            Fonte {{ i + 1 }}: {{ source.source }}
                            <mat-chip class="confidence-chip">
                              {{ (source.confidence * 100) | number:'1.0-0' }}%
                            </mat-chip>
                          </mat-panel-title>
                        </mat-expansion-panel-header>
                        <div class="source-content">
                          <p>{{ source.text }}</p>
                          <div class="source-metadata" *ngIf="source.metadata">
                            <span *ngIf="source.page">Pagina: {{ source.page }}</span>
                            <span *ngIf="source.metadata['file_type']">Tipo: {{ source.metadata['file_type'] }}</span>
                          </div>
                        </div>
                      </mat-expansion-panel>
                    </div>
                  </mat-card-content>
                  <mat-card-actions>
                    <button mat-button (click)="exportResult()">
                      <mat-icon>download</mat-icon>
                      Esporta Risultato
                    </button>
                    <button mat-button (click)="saveQuery()">
                      <mat-icon>bookmark</mat-icon>
                      Salva Query
                    </button>
                  </mat-card-actions>
                </mat-card>
              </div>
            </div>
          </mat-tab>

          <!-- Management Tab -->
          <mat-tab label="Gestione Database">
            <div class="tab-content">
              <div class="management-section">
                <mat-card class="stats-card">
                  <mat-card-header>
                    <mat-card-title>📊 Statistiche Database</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="stats-grid">
                      <div class="stat-item">
                        <mat-icon>description</mat-icon>
                        <div class="stat-content">
                          <div class="stat-value">{{ indexStats.total_documents }}</div>
                          <div class="stat-label">Documenti</div>
                        </div>
                      </div>
                      <div class="stat-item">
                        <mat-icon>storage</mat-icon>
                        <div class="stat-content">
                          <div class="stat-value">{{ formatVectorCount(indexStats.total_vectors) }}</div>
                          <div class="stat-label">Vettori</div>
                        </div>
                      </div>
                      <div class="stat-item">
                        <mat-icon>schedule</mat-icon>
                        <div class="stat-content">
                          <div class="stat-value">{{ indexStats.last_updated || 'N/A' }}</div>
                          <div class="stat-label">Ultimo Aggiornamento</div>
                        </div>
                      </div>
                    </div>
                  </mat-card-content>
                  <mat-card-actions>
                    <button mat-button (click)="refreshStats()">
                      <mat-icon>refresh</mat-icon>
                      Aggiorna
                    </button>
                    <button mat-button color="warn" (click)="clearDatabase()">
                      <mat-icon>delete_forever</mat-icon>
                      Cancella Database
                    </button>
                  </mat-card-actions>
                </mat-card>
              </div>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>

      <!-- Loading Overlay -->
      <app-loading
        *ngIf="isAnalyzing || isQuerying"
        type="overlay"
        [message]="loadingMessage">
      </app-loading>
    </div>
  `,
  styles: [`
    .document-rag-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 32px;

      h1 {
        font-size: 2rem;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #333;
      }

      p {
        font-size: 1rem;
        color: #666;
        margin: 0;
      }
    }

    .content-tabs {
      .mat-mdc-tab-group {
        margin-bottom: 32px;
      }
    }

    .tab-content {
      padding-top: 24px;
    }

    .analysis-config-card {
      margin-top: 24px;
    }

    .analysis-form,
    .query-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .query-options {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .results-card {
      margin-top: 24px;
    }

    .query-response {
      background: #f5f5f5;
      padding: 16px;
      border-radius: 4px;
      margin-bottom: 16px;
      border-left: 4px solid #3f51b5;

      p {
        margin: 0;
        line-height: 1.6;
      }
    }

    .sources-section {
      margin-top: 16px;

      h4 {
        margin: 0 0 16px 0;
        font-size: 1.1rem;
        font-weight: 500;
      }
    }

    .confidence-chip {
      margin-left: 8px;
      background: #e8f5e8;
      color: #2e7d32;
    }

    .source-content {
      p {
        margin-bottom: 12px;
        line-height: 1.6;
      }
    }

    .source-metadata {
      display: flex;
      gap: 16px;
      font-size: 0.8rem;
      color: #666;

      span {
        background: #f0f0f0;
        padding: 4px 8px;
        border-radius: 4px;
      }
    }

    .stats-card {
      margin-bottom: 24px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 24px;
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px;
      background: #f9f9f9;
      border-radius: 8px;

      mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: #3f51b5;
      }
    }

    .stat-content {
      .stat-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #333;
      }

      .stat-label {
        font-size: 0.9rem;
        color: #666;
      }
    }

    @media (max-width: 768px) {
      .document-rag-container {
        padding: 16px;
      }

      .query-options {
        grid-template-columns: 1fr;
      }

      .stats-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class DocumentRagComponent implements OnInit, OnDestroy {
  selectedTabIndex = 0;
  selectedFiles: File[] = [];
  analysisResults: DocumentAnalysis[] = [];
  queryResult: QueryResponse | null = null;
  indexStats: IndexStats = { total_documents: 0, total_vectors: 0 };

  isAnalyzing = false;
  isQuerying = false;
  loadingMessage = '';

  analysisForm: FormGroup;
  queryForm: FormGroup;

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private notificationService: NotificationService,
    private snackBar: MatSnackBar
  ) {
    this.analysisForm = this.fb.group({
      analysisType: ['automatic', Validators.required],
      notes: ['']
    });

    this.queryForm = this.fb.group({
      query: ['', [Validators.required, Validators.minLength(5)]],
      outputFormat: ['json', Validators.required],
      maxResults: [5, Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadIndexStats();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onFilesSelected(files: File[]): void {
    this.selectedFiles = files;
    this.notificationService.showInfo(
      'File Selezionati',
      `Selezionati ${files.length} file per l'analisi`
    );
  }

  onUploadCompleted(fileProgresses: FileUploadProgress[]): void {
    const successfulUploads = fileProgresses.filter(fp => fp.status === 'completed');
    this.notificationService.showSuccess(
      'Upload Completato',
      `${successfulUploads.length} file caricati con successo`
    );
  }

  startAnalysis(): void {
    if (this.selectedFiles.length === 0) return;

    this.isAnalyzing = true;
    this.loadingMessage = 'Caricamento documenti nel database...';

    // First upload all files to vector DB
    const uploadPromises = this.selectedFiles.map(file =>
      this.apiService.uploadFileToVectorDB(file).toPromise()
    );

    Promise.all(uploadPromises).then(() => {
      this.loadingMessage = 'Analizzando documenti...';

      // Then analyze all stored documents at once
      this.apiService.analyzeStoredDocuments()
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: (result) => {
            this.analysisResults = [result];
            this.isAnalyzing = false;
            this.loadingMessage = '';

            this.notificationService.showSuccess(
              'Analisi Completata',
              `Documenti caricati e analizzati con successo`
            );

            this.loadIndexStats();
            this.selectedTabIndex = 1; // Switch to query tab
          },
          error: (error) => {
            this.isAnalyzing = false;
            this.loadingMessage = '';
            this.notificationService.showError(
              'Errore Analisi',
              error.message || 'Errore durante l\'analisi dei documenti'
            );
          }
        });
    }).catch(error => {
      this.isAnalyzing = false;
      this.loadingMessage = '';
      this.notificationService.showError(
        'Errore Upload',
        'Errore durante il caricamento dei documenti'
      );
    });
  }

  executeQuery(): void {
    if (!this.queryForm.valid) return;

    this.isQuerying = true;
    this.loadingMessage = 'Cercando risposta...';

    const queryRequest: QueryRequest = {
      query: this.queryForm.value.query,
      output_format: this.queryForm.value.outputFormat,
      max_results: this.queryForm.value.maxResults
    };

    this.apiService.queryRAG(queryRequest)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.queryResult = result;
          this.isQuerying = false;
          this.loadingMessage = '';

          this.notificationService.showSuccess(
            'Query Completata',
            `Risposta trovata con confidenza ${(result.confidence * 100).toFixed(1)}%`
          );
        },
        error: (error) => {
          this.isQuerying = false;
          this.loadingMessage = '';
          this.notificationService.showError(
            'Errore Query',
            error.message || 'Errore durante la ricerca'
          );
        }
      });
  }

  clearQuery(): void {
    this.queryForm.reset({
      outputFormat: 'json',
      maxResults: 5
    });
    this.queryResult = null;
  }

  exportResult(): void {
    if (!this.queryResult) return;

    const data = {
      query: this.queryForm.value.query,
      result: this.queryResult,
      timestamp: new Date().toISOString()
    };

    this.apiService.exportToPDF(data, 'report').subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `query-result-${new Date().getTime()}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);

        this.notificationService.showSuccess(
          'Export Completato',
          'Report PDF scaricato con successo'
        );
      },
      error: (error) => {
        this.notificationService.showError(
          'Errore Export',
          'Errore durante l\'esportazione del PDF'
        );
      }
    });
  }

  saveQuery(): void {
    if (!this.queryResult) return;

    const savedQueries = JSON.parse(localStorage.getItem('savedQueries') || '[]');
    savedQueries.push({
      id: Date.now().toString(),
      query: this.queryForm.value.query,
      result: this.queryResult,
      timestamp: new Date().toISOString()
    });
    localStorage.setItem('savedQueries', JSON.stringify(savedQueries));

    this.snackBar.open('Query salvata con successo', 'Chiudi', { duration: 3000 });
  }

  loadIndexStats(): void {
    this.apiService.getIndexStats()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (stats) => {
          this.indexStats = stats;
        },
        error: (error) => {
          console.warn('Failed to load index stats:', error);
        }
      });
  }

  refreshStats(): void {
    this.loadIndexStats();
    this.notificationService.showInfo('Statistiche', 'Statistiche aggiornate');
  }

  clearDatabase(): void {
    if (confirm('Sei sicuro di voler cancellare tutto il database? Questa azione è irreversibile.')) {
      this.apiService.clearIndex().subscribe({
        next: () => {
          this.indexStats = { total_documents: 0, total_vectors: 0 };
          this.queryResult = null;
          this.notificationService.showSuccess(
            'Database Cancellato',
            'Tutti i documenti sono stati rimossi dal database'
          );
        },
        error: (error) => {
          this.notificationService.showError(
            'Errore',
            'Errore durante la cancellazione del database'
          );
        }
      });
    }
  }

  formatVectorCount(count: number): string {
    if (count < 1000) return count.toString();
    if (count < 1000000) return `${(count / 1000).toFixed(1)}K`;
    return `${(count / 1000000).toFixed(1)}M`;
  }
}