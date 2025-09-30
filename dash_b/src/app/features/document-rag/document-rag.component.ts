import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { Subject, takeUntil } from 'rxjs';

import { DocumentAnalysis, IndexStats, QueryRequest, QueryResponse } from '../../core/models/analysis.model';
import { FileUploadProgress } from '../../core/models/ui.model';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { FileUploadComponent } from '../../shared/components/file-upload/file-upload.component';
import { LoadingComponent } from '../../shared/components/loading/loading.component';
import { VoiceInputComponent } from '../../shared/components/voice-input/voice-input.component';
import { WebRTCVoiceComponent } from '../../shared/components/webrtc-voice/webrtc-voice.component';

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
    MatListModule,
    MatDividerModule,
    MatSnackBarModule,
    LoadingComponent,
    FileUploadComponent,
    VoiceInputComponent,
    WebRTCVoiceComponent
  ],
  template: `
    <div class="document-rag-container">
      <div class="page-header">
        <h1><mat-icon class="title-icon">folder</mat-icon> Gestione Documenti RAG</h1>
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
                      <mat-form-field appearance="outline" class="full-width field-enhanced">
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

                      <mat-form-field appearance="outline" class="full-width field-enhanced">
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

                <!-- Analysis Results Display -->
                <mat-card *ngIf="analysisResults.length > 0" class="analysis-results-card">
                  <mat-card-header>
                    <mat-card-title>📊 Risultati Analisi Documenti</mat-card-title>
                    <mat-card-subtitle>
                      Analizzati {{ selectedFiles.length }} documenti
                    </mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Analisi Completa</mat-label>
                      <textarea
                        matInput
                        [value]="currentAnalysisText"
                        rows="15"
                        readonly
                        class="analysis-text">
                      </textarea>
                    </mat-form-field>

                    <!-- Metadata Display -->
                    <div class="analysis-metadata" *ngIf="currentAnalysis?.analysis">
                      <mat-chip-listbox aria-label="Metadata">
                        <mat-chip-option disabled>
                          <mat-icon>confidence</mat-icon>
                          Confidenza: {{ (currentConfidence * 100) | number:'1.0-0' }}%
                        </mat-chip-option>
                        <mat-chip-option disabled>
                          <mat-icon>timer</mat-icon>
                          Tempo: {{ currentProcessingTime | number:'1.1-1' }}s
                        </mat-chip-option>
                        <mat-chip-option disabled *ngIf="currentAnalysis?.file_info?.pages">
                          <mat-icon>description</mat-icon>
                          Pagine: {{ currentAnalysis.file_info?.pages }}
                        </mat-chip-option>
                        <mat-chip-option disabled *ngIf="currentAnalysis?.file_info?.has_tables">
                          <mat-icon>table_chart</mat-icon>
                          Tabelle trovate
                        </mat-chip-option>
                      </mat-chip-listbox>
                    </div>

                    <!-- Sources Section -->
                    <div class="sources-section" *ngIf="currentAnalysis?.sources && currentAnalysis.sources.length > 0">
                      <h4>📚 Fonti Utilizzate</h4>
                      <mat-list>
                        <mat-list-item *ngFor="let source of currentAnalysis?.sources || []">
                          <mat-icon matListItemIcon>source</mat-icon>
                          <div matListItemTitle>{{ source.source }}</div>
                          <div matListItemLine>
                            Confidenza: {{ (source.confidence * 100) | number:'1.0-0' }}%
                            <span *ngIf="source.page"> • Pagina: {{ source.page }}</span>
                          </div>
                        </mat-list-item>
                      </mat-list>
                    </div>
                  </mat-card-content>
                  <mat-card-actions class="analysis-actions">
                    <button
                      mat-raised-button
                      color="primary"
                      class="dark-mode-btn primary-btn"
                      (click)="exportAnalysisPDF()">
                      <mat-icon>picture_as_pdf</mat-icon>
                      Esporta PDF
                    </button>
                    <button
                      mat-button
                      class="dark-mode-btn secondary-btn"
                      (click)="copyAnalysisToClipboard()">
                      <mat-icon>content_copy</mat-icon>
                      Copia Testo
                    </button>
                    <button
                      mat-button
                      color="warn"
                      class="dark-mode-btn warn-btn"
                      (click)="clearAnalysis()">
                      <mat-icon>clear</mat-icon>
                      Cancella Analisi
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
                  <mat-card-content>
                    <form [formGroup]="queryForm" class="query-form">
                      <mat-form-field appearance="outline" class="full-width field-enhanced">
                        <mat-label>Inserisci la tua domanda</mat-label>
                        <textarea
                          matInput
                          formControlName="query"
                          placeholder="Es: Qual è l'EBITDA dell'azienda negli ultimi tre anni?"
                          rows="3">
                        </textarea>
                      </mat-form-field>
                    </form>
                  </mat-card-content>
                  <mat-card-actions class="query-actions">
                    <button
                      mat-raised-button
                      color="primary"
                      (click)="executeManualQuery()"
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

                    <!-- Voice Input Component -->
                    <app-voice-input
                      #voiceInput
                      [showMessages]="true"
                      (transcriptReceived)="onVoiceTranscriptReceived($event)"
                      (sessionStarted)="onVoiceSessionStarted()"
                      (sessionEnded)="onVoiceSessionEnded()">
                    </app-voice-input>

                    <!-- WebRTC Voice Component (Premium) -->
                    <app-webrtc-voice
                      #webrtcVoice
                      [autoConnect]="false"
                      (transcriptReceived)="onWebRTCTranscriptReceived($event)"
                      (connectionStateChanged)="onWebRTCStateChanged($event)"
                      (audioDataReceived)="onWebRTCAudioReceived($event)">
                    </app-webrtc-voice>

                    <!-- Test Text Button -->
                    <button
                      mat-button
                      color="accent"
                      (click)="sendTestMessage()"
                      [disabled]="!isVoiceSessionActive">
                      <mat-icon>bug_report</mat-icon>
                      Test Testo
                    </button>

                    <!-- Test Transcript Event Button -->
                    <button
                      mat-button
                      color="warn"
                      (click)="testTranscriptEvent()">
                      <mat-icon>record_voice_over</mat-icon>
                      Test Transcript
                    </button>

                    <!-- Test Voice Quality Button -->
                    <button
                      mat-button
                      color="accent"
                      (click)="testVoiceQuality()">
                      <mat-icon>volume_up</mat-icon>
                      Test Voce
                    </button>
                    <div class="results-selector">
                      <mat-form-field appearance="outline" class="compact-field">
                        <mat-label>Risultati</mat-label>
                        <mat-select [value]="queryForm.get('maxResults')?.value"
                                   (selectionChange)="queryForm.patchValue({maxResults: $event.value})">
                          <mat-option [value]="3">3</mat-option>
                          <mat-option [value]="5">5</mat-option>
                          <mat-option [value]="10">10</mat-option>
                        </mat-select>
                      </mat-form-field>
                    </div>
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
                    <mat-card-title><mat-icon class="card-icon">analytics</mat-icon> Statistiche Database</mat-card-title>
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
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 2rem;
        font-weight: 600;
        margin: 0 0 8px 0;
        color: #333;

        .title-icon {
          font-size: 2.2rem !important;
          width: 2.2rem !important;
          height: 2.2rem !important;
          color: #667eea !important;
        }
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


    .full-width {
      width: 100%;
    }

    .card-icon {
      font-size: 1.4rem !important;
      width: 1.4rem !important;
      height: 1.4rem !important;
      color: #667eea !important;
      margin-right: 8px !important;
      vertical-align: middle !important;
    }

    .query-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;

      .results-selector {
        margin-left: auto;
      }
    }

    .compact-field {
      width: 120px;

      ::ng-deep .mat-mdc-form-field-wrapper {
        padding: 0;
      }

      ::ng-deep .mat-mdc-text-field-wrapper {
        padding: 8px 12px;
      }

      ::ng-deep .mat-mdc-form-field-infix {
        padding: 12px 0;
        min-height: 40px;
      }

      ::ng-deep .mat-mdc-select-trigger {
        padding: 12px 8px;
      }
    }

    /* Analysis Results Card Styles */
    .analysis-results-card {
      margin-top: 24px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

      mat-card-header {
        background: rgba(255, 255, 255, 0.95);
        padding: 16px;
        border-radius: 8px 8px 0 0;
        margin: -16px -16px 16px -16px;
      }

      .analysis-text {
        font-family: 'Roboto', sans-serif;
        line-height: 1.6;
        padding: 12px;
        border-radius: 4px;

        /* Light mode styles */
        background: #f9f9f9;
        border: 1px solid #e0e0e0;
        color: #333;

        /* Dark mode support - uses CSS variables from Angular Material theme */
        @media (prefers-color-scheme: dark) {
          background: #2d2d30;
          border: 1px solid #404040;
          color: #e1e1e1;
        }

        /* Additional dark mode support via CSS class */
        :host-context(.dark-theme) & {
          background: #2d2d30 !important;
          border: 1px solid #404040 !important;
          color: #e1e1e1 !important;
        }

        /* Ensure text is always visible regardless of theme */
        &:focus {
          outline: 2px solid #667eea;
          outline-offset: 2px;
        }
      }

      .analysis-metadata {
        margin: 16px 0;

        mat-chip-listbox {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        mat-chip-option {
          background: rgba(102, 126, 234, 0.1);
          color: #333;

          mat-icon {
            font-size: 18px;
            margin-right: 4px;
          }
        }
      }

      .sources-section {
        margin-top: 24px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 8px;

        h4 {
          margin-bottom: 12px;
          color: #667eea;
        }
      }

      mat-card-content {
        background: white;
        padding: 24px;
        border-radius: 8px;
      }

      mat-card-actions {
        background: rgba(255, 255, 255, 0.95);
        padding: 16px;
        border-radius: 0 0 8px 8px;
        margin: 16px -16px -16px -16px;

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
          background: rgba(45, 45, 48, 0.95);
        }

        :host-context(.dark-theme) & {
          background: rgba(45, 45, 48, 0.95);
        }
      }

      /* Dark Mode Button Fixes - Direct approach */
      .analysis-actions {
        @media (prefers-color-scheme: dark) {
          background: rgba(45, 45, 48, 0.95) !important;
        }
      }

      .dark-mode-btn {
        @media (prefers-color-scheme: dark) {
          color: #ffffff !important;
          background-color: rgba(66, 66, 66, 0.8) !important;
          border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }
      }

      .dark-mode-btn.primary-btn {
        @media (prefers-color-scheme: dark) {
          background-color: #1976d2 !important;
          color: #ffffff !important;
        }
      }

      .dark-mode-btn.warn-btn {
        @media (prefers-color-scheme: dark) {
          background-color: #d32f2f !important;
          color: #ffffff !important;
        }
      }

      .dark-mode-btn .mat-icon {
        @media (prefers-color-scheme: dark) {
          color: #ffffff !important;
        }
      }
    }

    /* Enhanced field padding for better UX */
    .field-enhanced {
      ::ng-deep .mat-mdc-form-field-wrapper {
        padding: 8px 0;
      }

      ::ng-deep .mat-mdc-text-field-wrapper {
        padding: 16px 20px;
      }

      ::ng-deep .mat-mdc-form-field-infix {
        padding: 20px 0;
        min-height: 60px;
      }

      ::ng-deep .mat-mdc-select-trigger {
        padding: 20px 16px;
      }

      ::ng-deep textarea.mat-mdc-input-element {
        padding: 12px 0;
        line-height: 1.6;
      }
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

    /* Voice messages full width override */
    ::ng-deep app-voice-input .voice-messages {
      position: relative;
      width: calc(100vw - 48px) !important;
      max-width: calc(100vw - 48px) !important;
      left: calc(-50vw + 50% + 24px) !important;
      margin-left: 0 !important;
      margin-right: 0 !important;
    }

    @media (max-width: 768px) {
      .document-rag-container {
        padding: 16px;
      }

      ::ng-deep app-voice-input .voice-messages {
        width: calc(100vw - 32px) !important;
        max-width: calc(100vw - 32px) !important;
        left: calc(-50vw + 50% + 16px) !important;
      }

      .stats-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class DocumentRagComponent implements OnInit, OnDestroy {
  @ViewChild('voiceInput') voiceInputComponent!: VoiceInputComponent;
  @ViewChild('webrtcVoice') webrtcVoiceComponent!: WebRTCVoiceComponent;

  selectedTabIndex = 0;
  selectedFiles: File[] = [];
  analysisResults: DocumentAnalysis[] = [];
  queryResult: QueryResponse | null = null;
  indexStats: IndexStats = { total_documents: 0, total_vectors: 0 };

  isAnalyzing = false;
  isQuerying = false;
  isVoiceSessionActive = false;
  isVoiceQuery = false; // Track if current query came from voice
  isWebRTCActive = false; // Track WebRTC connection status
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
            console.log('API Response received:', result);
            console.log('Type of result:', typeof result);
            console.log('Result keys:', Object.keys(result || {}));
            this.analysisResults = [result];
            console.log('analysisResults after assignment:', this.analysisResults);
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
            console.log('Analysis Error:', error);
            console.log('Error type:', typeof error);
            console.log('Error message:', error.message);
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

  executeManualQuery(): void {
    this.isVoiceQuery = false; // Ensure this is marked as manual query
    this.executeQuery();
  }

  executeQuery(): void {
    if (!this.queryForm.valid) return;

    this.isQuerying = true;
    this.loadingMessage = 'Cercando risposta...';

    const queryRequest: QueryRequest = {
      query: this.queryForm.value.query,
      output_format: 'json',
      max_results: this.queryForm.value.maxResults
    };

    this.apiService.queryRAG(queryRequest)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          // Only set queryResult if NOT a voice query (to avoid double display)
          if (!this.isVoiceQuery) {
            this.queryResult = result;
          }

          this.isQuerying = false;
          this.loadingMessage = '';

          // Add assistant response to voice messages if voice query
          if (this.isVoiceQuery && this.voiceInputComponent?.voiceChatService) {
            this.voiceInputComponent.voiceChatService.addAssistantMessage(result.response);

            // Speak the response if it's a voice query
            this.voiceInputComponent.voiceChatService.speakText(result.response);
          }

          this.notificationService.showSuccess(
            'Query Completata',
            `Risposta trovata con confidenza ${(result.confidence * 100).toFixed(1)}%`
          );

          // Reset voice query flag
          this.isVoiceQuery = false;
        },
        error: (error) => {
          this.isQuerying = false;
          this.loadingMessage = '';
          this.isVoiceQuery = false; // Reset flag on error too

          this.notificationService.showError(
            'Errore Query',
            error.message || 'Errore durante la ricerca'
          );
        }
      });
  }

  clearQuery(): void {
    this.queryForm.reset({
      maxResults: 5
    });
    this.queryResult = null;
  }

  exportResult(): void {
    if (!this.queryResult) return;

    // Use the new FastAPI endpoint for professional PDF generation
    this.apiService.exportQASessionToPDF(
      this.queryForm.value.query,
      this.queryResult.response,
      this.queryResult.sources,
      {
        confidence: this.queryResult.confidence,
        processing_time: this.queryResult.processing_time,
        query_type: 'RAG Query',
        timestamp: new Date().toLocaleString('it-IT')
      }
    ).subscribe({
      next: (blob) => {
        // Direct download of professional PDF
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `qa_session_${new Date().toISOString().split('T')[0]}.pdf`;
        link.click();

        // Cleanup
        setTimeout(() => {
          window.URL.revokeObjectURL(url);
        }, 1000);

        this.notificationService.showSuccess(
          'PDF Esportato',
          'Sessione Q&A esportata con successo in PDF professionale'
        );
      },
      error: (error) => {
        console.error('PDF export error:', error);
        this.notificationService.showError(
          'Errore Export',
          'Errore durante l\'esportazione del PDF. Riprova più tardi.'
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

  // Voice Input Event Handlers
  onVoiceTranscriptReceived(transcript: string): void {
    console.log('📝 onVoiceTranscriptReceived called with:', transcript);
    if (transcript && transcript.trim()) {
      // Add user message to voice chat
      if (this.voiceInputComponent?.voiceChatService) {
        this.voiceInputComponent.voiceChatService.addUserMessage(transcript);
      }

      // Set the transcript in the query form
      this.queryForm.patchValue({ query: transcript });

      // Mark this as a voice query
      this.isVoiceQuery = true;

      // Show notification
      this.notificationService.showSuccess(
        'Trascrizione Vocale',
        'Domanda trascritta - Invio al RAG...'
      );

      // Automatically execute the query through RAG backend
      this.executeQuery();
    }
  }

  onVoiceSessionStarted(): void {
    this.isVoiceSessionActive = true;
    console.log('Voice session started');
  }

  onVoiceSessionEnded(): void {
    this.isVoiceSessionActive = false;
    console.log('Voice session ended');
  }

  sendTestMessage(): void {
    // Send a test text message to OpenAI
    const testMessage = 'Ciao, questo è un messaggio di test. Come stai?';

    // Use ViewChild to access the voice service
    if (this.voiceInputComponent && this.voiceInputComponent.voiceChatService) {
      this.voiceInputComponent.voiceChatService.sendTextMessage(testMessage);

      this.notificationService.showSuccess(
        'Test Inviato',
        `Messaggio di test: "${testMessage}"`
      );
      console.log('Test message sent:', testMessage);
    } else {
      this.notificationService.showError(
        'Errore',
        'Servizio vocale non disponibile. Assicurati di aver avviato la sessione vocale.'
      );
      console.error('Voice service not available');
    }
  }

  testTranscriptEvent(): void {
    console.log('🧪 Testing transcript event...');
    const testTranscript = 'lista dettagliata costi';

    // Directly call the onVoiceTranscriptReceived method to test if it works
    this.onVoiceTranscriptReceived(testTranscript);

    console.log('🧪 Test completed - check console for onVoiceTranscriptReceived log');
  }

  testVoiceQuality(): void {
    console.log('🎙️ Testing voice quality...');

    if (this.voiceInputComponent?.voiceChatService) {
      // Show available voices in console
      const voices = this.voiceInputComponent.voiceChatService.getAvailableItalianVoices();
      console.log('🎙️ Available Italian voices:', voices.map(v => `${v.name} (${v.lang}) - Local: ${v.localService}`));

      // Test voice with a comprehensive sample text showcasing improvements
      const testText = `Benvenuto al sistema avanzato di sintesi vocale!

      Questo test dimostra i miglioramenti implementati:

      1. Pronuncia più naturale con pause appropriate.
      2. Gestione migliorata di numeri come 1.234 euro e percentuali come 15 per cento.
      3. Acronimi finanziari come E-BIT-DA, R-O-I ed E-BIT vengono pronunciati correttamente.

      La voce risulta ora meno robotica e più professionale per l'analisi finanziaria aziendale.`;

      this.voiceInputComponent.voiceChatService.speakText(testText);

      this.notificationService.showSuccess(
        'Test Voce',
        'Prova della qualità vocale in corso. Controlla la console per i dettagli delle voci disponibili.'
      );
    } else {
      this.notificationService.showError(
        'Errore',
        'Servizio vocale non disponibile'
      );
    }
  }

  onVoiceSessionChanged(isActive: boolean): void {
    this.isVoiceSessionActive = isActive;

    if (isActive) {
      this.notificationService.showInfo(
        'Sessione Vocale',
        'Ora puoi parlare per inserire la tua domanda'
      );
    } else {
      this.notificationService.showInfo(
        'Sessione Vocale',
        'Sessione vocale terminata'
      );
    }
  }

  // WebRTC Voice Event Handlers
  onWebRTCTranscriptReceived(transcript: string): void {
    console.log('🎙️ WebRTC transcript received:', transcript);
    if (transcript && transcript.trim()) {
      // Set the transcript in the query form
      this.queryForm.patchValue({ query: transcript });

      // Mark this as a voice query
      this.isVoiceQuery = true;

      // Show notification with premium badge
      this.notificationService.showSuccess(
        'WebRTC Premium',
        '🎙️ Trascrizione real-time - Invio al RAG...'
      );

      // Automatically execute the query through RAG backend
      this.executeQuery();
    }
  }

  onWebRTCStateChanged(state: any): void {
    this.isWebRTCActive = state.isConnected;

    if (state.isConnected) {
      this.notificationService.showSuccess(
        'WebRTC Connesso',
        '🚀 Audio real-time attivo - Qualità premium'
      );
    } else if (state.error) {
      this.notificationService.showError(
        'WebRTC Errore',
        state.error
      );
    }
  }

  onWebRTCAudioReceived(audioData: ArrayBuffer): void {
    console.log('🎵 WebRTC audio data received:', audioData.byteLength, 'bytes');
    // Audio data is handled automatically by the WebRTC component
    // This event is just for monitoring/logging
  }

  // New methods for Analysis PDF Export
  exportAnalysisPDF(): void {
    if (!this.analysisResults || this.analysisResults.length === 0) {
      this.notificationService.showWarning(
        'Nessuna Analisi',
        'Nessuna analisi disponibile da esportare'
      );
      return;
    }

    const analysisText = this.currentAnalysisText;
    const metadata = {
      numero_documenti: this.selectedFiles.length,
      timestamp: new Date().toLocaleString('it-IT'),
      confidenza: `${((this.currentConfidence || 0) * 100).toFixed(0)}%`,
      tempo_elaborazione: `${(this.currentProcessingTime || 0).toFixed(1)}s`,
      tipo_analisi: 'Analisi Documenti RAG'
    };

    // Call the new FastAPI endpoint for professional PDF generation
    this.apiService.exportAnalysisToPDF(analysisText, metadata)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (blob) => {
          // Direct download of professional PDF
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `Analisi_Documenti_${new Date().toISOString().split('T')[0]}.pdf`;
          link.click();

          setTimeout(() => {
            window.URL.revokeObjectURL(url);
          }, 1000);

          this.notificationService.showSuccess(
            'PDF Generato',
            'Il PDF professionale è stato scaricato con successo'
          );
        },
        error: (error) => {
          console.error('PDF export error:', error);
          this.notificationService.showError(
            'Errore Export',
            'Errore durante l\'esportazione PDF. Riprova più tardi.'
          );
        }
      });
  }

  copyAnalysisToClipboard(): void {
    if (!this.analysisResults || this.analysisResults.length === 0) {
      this.notificationService.showWarning(
        'Nessuna Analisi',
        'Nessuna analisi disponibile da copiare'
      );
      return;
    }

    const analysisText = this.currentAnalysisText;
    navigator.clipboard.writeText(analysisText).then(() => {
      this.notificationService.showSuccess(
        'Copiato',
        'Analisi copiata negli appunti'
      );
    }).catch(() => {
      this.notificationService.showError(
        'Errore',
        'Impossibile copiare il testo'
      );
    });
  }

  clearAnalysis(): void {
    this.analysisResults = [];
    this.selectedFiles = [];
    this.notificationService.showInfo(
      'Analisi Cancellata',
      'I risultati dell\'analisi sono stati rimossi'
    );
  }

  get currentAnalysis() {
    return this.analysisResults?.[0];
  }

  get currentAnalysisData() {
    return this.currentAnalysis;
  }

  get currentAnalysisText() {
    return this.currentAnalysis?.analysis || '';
  }

  get currentConfidence() {
    return this.currentAnalysis?.confidence || 0;
  }

  get currentProcessingTime() {
    return this.currentAnalysis?.processing_time || 0;
  }
}