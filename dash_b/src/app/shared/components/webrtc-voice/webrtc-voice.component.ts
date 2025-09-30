import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { FormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';

import { OpenAIWebRTCService, WebRTCSessionState } from '../../../core/services/openai-webrtc.service';

export interface WebRTCVoiceConfig {
  apiKey: string;
  voice: string;
  language: string;
  temperature: number;
  instructions: string;
}

export interface VoiceTranscript {
  text: string;
  timestamp: Date;
  confidence?: number;
}

@Component({
  selector: 'app-webrtc-voice',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSliderModule,
    MatTooltipModule
  ],
  template: `
    <div class="webrtc-voice-container">
      <!-- Configuration Panel -->
      <mat-card class="config-card" *ngIf="!sessionState.isConnected">
        <mat-card-header>
          <mat-card-title>
            <mat-icon class="title-icon">settings_voice</mat-icon>
            Configurazione WebRTC Real-time
          </mat-card-title>
          <mat-card-subtitle>
            🎙️ Connessione diretta con OpenAI Realtime API
          </mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <form [formGroup]="configForm" class="config-form">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>OpenAI API Key</mat-label>
              <input matInput type="password" formControlName="apiKey"
                     placeholder="sk-proj-..." required>
              <mat-icon matSuffix>key</mat-icon>
              <mat-hint>Inserisci la tua API key OpenAI per WebRTC real-time</mat-hint>
            </mat-form-field>

            <div class="form-row">
              <mat-form-field appearance="outline">
                <mat-label>Voce</mat-label>
                <mat-select formControlName="voice">
                  <mat-option value="alloy">Alloy (Neutrale)</mat-option>
                  <mat-option value="echo">Echo (Maschile)</mat-option>
                  <mat-option value="fable">Fable (Britannico)</mat-option>
                  <mat-option value="onyx">Onyx (Profondo)</mat-option>
                  <mat-option value="nova">Nova (Femminile)</mat-option>
                  <mat-option value="shimmer">Shimmer (Dolce)</mat-option>
                </mat-select>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Lingua</mat-label>
                <mat-select formControlName="language">
                  <mat-option value="it-IT">Italiano</mat-option>
                  <mat-option value="en-US">Inglese (US)</mat-option>
                  <mat-option value="en-GB">Inglese (UK)</mat-option>
                </mat-select>
              </mat-form-field>
            </div>

            <div class="slider-field">
              <label>Temperatura: {{ configForm.get('temperature')?.value }}</label>
              <input type="range"
                     min="0"
                     max="1"
                     step="0.1"
                     [value]="configForm.get('temperature')?.value"
                     (input)="onTemperatureChange($event)"
                     class="temperature-slider">
              <div class="slider-help">
                Controlla la creatività delle risposte (0 = conservativo, 1 = creativo)
              </div>
            </div>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Istruzioni Sistema</mat-label>
              <textarea matInput formControlName="instructions" rows="3"
                        placeholder="Sei un assistente AI specializzato in..."></textarea>
            </mat-form-field>
          </form>
        </mat-card-content>
        <mat-card-actions>
          <button mat-raised-button color="primary"
                  (click)="connect()"
                  [disabled]="!configForm.valid || sessionState.isConnecting">
            <mat-icon>wifi</mat-icon>
            {{ sessionState.isConnecting ? 'Connessione...' : 'Connetti WebRTC' }}
          </button>
        </mat-card-actions>
      </mat-card>

      <!-- Voice Control Panel -->
      <mat-card class="control-card" *ngIf="sessionState.isConnected">
        <mat-card-header>
          <mat-card-title>
            <mat-icon class="title-icon connected">radio_button_checked</mat-icon>
            Audio Real-time OpenAI
          </mat-card-title>
          <mat-card-subtitle>
            Sessione: {{ sessionState.sessionId }} •
            Stato: {{ getConnectionStatusText() }} •
            Modello: gpt-4o-realtime-preview
          </mat-card-subtitle>
        </mat-card-header>
        <mat-card-content>
          <!-- Audio Status Indicators -->
          <div class="status-indicators">
            <div class="status-item" [class.active]="sessionState.isRecording">
              <mat-icon>mic</mat-icon>
              <span>{{ sessionState.isRecording ? 'Ascolto...' : 'In attesa' }}</span>
            </div>
            <div class="status-item" [class.active]="sessionState.isSpeaking">
              <mat-icon>volume_up</mat-icon>
              <span>{{ sessionState.isSpeaking ? 'Parlando...' : 'Silenzio' }}</span>
            </div>
          </div>

          <!-- Recording Controls -->
          <div class="voice-controls">
            <button mat-fab color="primary"
                    [class.recording]="sessionState.isRecording"
                    (click)="toggleRecording()"
                    matTooltip="Attiva/Disattiva microfono">
              <mat-icon>{{ sessionState.isRecording ? 'mic' : 'mic_off' }}</mat-icon>
            </button>

            <button mat-stroked-button
                    (click)="sendTestMessage()"
                    [disabled]="sessionState.isSpeaking">
              <mat-icon>chat</mat-icon>
              Test Messaggio
            </button>

            <button mat-stroked-button color="warn"
                    (click)="cancelResponse()"
                    [disabled]="!sessionState.isSpeaking">
              <mat-icon>stop</mat-icon>
              Interrompi
            </button>
          </div>

          <!-- Text Input for Testing -->
          <div class="text-input-section" *ngIf="showTextInput">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Messaggio di testo</mat-label>
              <input matInput [(ngModel)]="textMessage"
                     placeholder="Scrivi un messaggio da inviare..."
                     (keydown.enter)="sendTextMessage()">
              <button matSuffix mat-icon-button (click)="sendTextMessage()"
                      [disabled]="!textMessage || !textMessage.trim()">
                <mat-icon>send</mat-icon>
              </button>
            </mat-form-field>
          </div>

          <!-- Transcript Display -->
          <div class="transcript-section" *ngIf="transcripts.length > 0">
            <h4>
              <mat-icon>record_voice_over</mat-icon>
              Trascrizioni
            </h4>
            <div class="transcript-list">
              <div *ngFor="let transcript of transcripts; trackBy: trackTranscript"
                   class="transcript-item">
                <div class="transcript-time">
                  {{ transcript.timestamp | date:'HH:mm:ss' }}
                  <span *ngIf="transcript.confidence" class="confidence">
                    ({{ (transcript.confidence * 100) | number:'1.0-0' }}%)
                  </span>
                </div>
                <div class="transcript-text">{{ transcript.text }}</div>
              </div>
            </div>
          </div>

          <!-- Audio Device Selection -->
          <div class="device-selection" *ngIf="audioDevices.length > 1">
            <mat-form-field appearance="outline">
              <mat-label>Dispositivo Audio</mat-label>
              <mat-select [value]="selectedDeviceId" (selectionChange)="switchAudioDevice($event.value)">
                <mat-option *ngFor="let device of audioDevices" [value]="device.deviceId">
                  {{ device.label || 'Dispositivo senza nome' }}
                </mat-option>
              </mat-select>
            </mat-form-field>
          </div>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button (click)="toggleTextInput()">
            <mat-icon>{{ showTextInput ? 'keyboard_hide' : 'keyboard' }}</mat-icon>
            {{ showTextInput ? 'Nascondi' : 'Mostra' }} Input Testo
          </button>
          <button mat-button color="warn" (click)="disconnect()">
            <mat-icon>wifi_off</mat-icon>
            Disconnetti
          </button>
        </mat-card-actions>
      </mat-card>

      <!-- Error Display -->
      <mat-card class="error-card" *ngIf="sessionState.error">
        <mat-card-content>
          <div class="error-content">
            <mat-icon color="warn">error</mat-icon>
            <div>
              <strong>Errore WebRTC</strong>
              <p>{{ sessionState.error }}</p>
            </div>
          </div>
        </mat-card-content>
        <mat-card-actions>
          <button mat-button (click)="clearError()">
            <mat-icon>clear</mat-icon>
            Cancella Errore
          </button>
          <button mat-raised-button color="primary" (click)="connect()">
            <mat-icon>refresh</mat-icon>
            Riprova Connessione
          </button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    .webrtc-voice-container {
      display: flex;
      flex-direction: column;
      gap: 20px;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }

    .title-icon {
      margin-right: 8px;
      vertical-align: middle;

      &.connected {
        color: #4caf50;
      }
    }

    .config-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .slider-field {
      margin: 16px 0;

      label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: #666;
      }

      .temperature-slider {
        width: 100%;
        margin: 8px 0;
      }

      .slider-help {
        font-size: 12px;
        color: #888;
        margin-top: 4px;
      }
    }

    .status-indicators {
      display: flex;
      gap: 24px;
      margin-bottom: 24px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #666;
      transition: all 0.3s ease;

      &.active {
        color: #4caf50;
        font-weight: 500;

        mat-icon {
          animation: pulse 1.5s infinite;
        }
      }

      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .voice-controls {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;

      .mat-mdc-fab {
        transition: all 0.3s ease;

        &.recording {
          background-color: #f44336 !important;
          animation: recordingPulse 1s infinite;
        }
      }
    }

    @keyframes recordingPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.1); }
    }

    .text-input-section {
      margin-bottom: 24px;
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;
    }

    .transcript-section {
      margin-bottom: 24px;

      h4 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        color: #333;
      }
    }

    .transcript-list {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
    }

    .transcript-item {
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }
    }

    .transcript-time {
      font-size: 12px;
      color: #666;
      margin-bottom: 4px;

      .confidence {
        color: #4caf50;
        font-weight: 500;
      }
    }

    .transcript-text {
      font-size: 14px;
      line-height: 1.5;
      color: #333;
    }

    .device-selection {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
    }

    .error-card {
      border-left: 4px solid #f44336;
    }

    .error-content {
      display: flex;
      align-items: flex-start;
      gap: 12px;

      mat-icon {
        margin-top: 2px;
      }

      div {
        flex: 1;

        strong {
          display: block;
          margin-bottom: 4px;
        }

        p {
          margin: 0;
          color: #666;
        }
      }
    }

    @media (max-width: 768px) {
      .webrtc-voice-container {
        padding: 16px;
      }

      .form-row {
        grid-template-columns: 1fr;
      }

      .voice-controls {
        justify-content: center;
      }

      .status-indicators {
        flex-direction: column;
        gap: 12px;
      }
    }
  `]
})
export class WebRTCVoiceComponent implements OnInit, OnDestroy {
  @Input() autoConnect: boolean = false;
  @Input() initialConfig?: Partial<WebRTCVoiceConfig>;

  @Output() transcriptReceived = new EventEmitter<string>();
  @Output() connectionStateChanged = new EventEmitter<WebRTCSessionState>();
  @Output() audioDataReceived = new EventEmitter<ArrayBuffer>();
  @Output() errorOccurred = new EventEmitter<string>();

  configForm: FormGroup;
  sessionState: WebRTCSessionState = {
    isConnected: false,
    isConnecting: false,
    isRecording: false,
    isSpeaking: false
  };

  transcripts: VoiceTranscript[] = [];
  audioDevices: MediaDeviceInfo[] = [];
  selectedDeviceId: string = '';
  showTextInput: boolean = false;
  textMessage: string = '';

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private webrtcService: OpenAIWebRTCService,
    private snackBar: MatSnackBar
  ) {
    this.configForm = this.fb.group({
      apiKey: ['', Validators.required],
      voice: ['alloy', Validators.required],
      language: ['it-IT', Validators.required],
      temperature: [0.7, [Validators.required, Validators.min(0), Validators.max(1)]],
      instructions: ['Sei un assistente AI specializzato nell\'analisi di documenti finanziari. Rispondi in italiano con un tono professionale e preciso.', Validators.required]
    });
  }

  async ngOnInit(): Promise<void> {
    // Apply initial configuration if provided
    if (this.initialConfig) {
      this.configForm.patchValue(this.initialConfig);
    }

    // Subscribe to WebRTC service events
    this.webrtcService.sessionState$
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        this.sessionState = state;
        this.connectionStateChanged.emit(state);
      });

    this.webrtcService.transcript$
      .pipe(takeUntil(this.destroy$))
      .subscribe(transcript => {
        const voiceTranscript: VoiceTranscript = {
          text: transcript,
          timestamp: new Date()
        };
        this.transcripts.push(voiceTranscript);
        this.transcriptReceived.emit(transcript);
      });

    this.webrtcService.audioData$
      .pipe(takeUntil(this.destroy$))
      .subscribe(audioData => {
        this.audioDataReceived.emit(audioData);
      });

    this.webrtcService.error$
      .pipe(takeUntil(this.destroy$))
      .subscribe(error => {
        this.snackBar.open(`Errore WebRTC: ${error}`, 'Chiudi', { duration: 5000 });
        this.errorOccurred.emit(error);
      });

    // Load audio devices
    await this.loadAudioDevices();

    // Auto-connect if requested
    if (this.autoConnect && this.configForm.valid) {
      this.connect();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.webrtcService.disconnect();
  }

  async connect(): Promise<void> {
    if (!this.configForm.valid) {
      this.snackBar.open('Configurazione non valida', 'Chiudi', { duration: 3000 });
      return;
    }

    try {
      const config = this.configForm.value;

      // Update session configuration
      this.webrtcService.updateSessionConfig({
        voice: config.voice,
        instructions: config.instructions,
        temperature: config.temperature
      });

      await this.webrtcService.connectToOpenAI(config.apiKey);

      this.snackBar.open('Connesso a OpenAI WebRTC!', 'Chiudi', { duration: 3000 });
    } catch (error) {
      console.error('Failed to connect:', error);
      this.snackBar.open('Connessione fallita', 'Chiudi', { duration: 5000 });
    }
  }

  async disconnect(): Promise<void> {
    await this.webrtcService.disconnect();
    this.transcripts = [];
    this.snackBar.open('Disconnesso da WebRTC', 'Chiudi', { duration: 3000 });
  }

  toggleRecording(): void {
    if (this.sessionState.isRecording) {
      this.webrtcService.stopRecording();
    } else {
      this.webrtcService.startRecording();
    }
  }

  sendTestMessage(): void {
    const testMessage = 'Ciao OpenAI! Questo è un test della connessione WebRTC real-time. Puoi confermare che stai ricevendo questo messaggio attraverso il canale dati WebRTC?';
    this.webrtcService.sendTextMessage(testMessage);

    // Add to transcript display
    this.transcripts.push({
      text: `[TEST REAL-TIME] ${testMessage}`,
      timestamp: new Date()
    });

    this.snackBar.open('Messaggio inviato via WebRTC a OpenAI', 'Chiudi', { duration: 3000 });
  }

  sendTextMessage(): void {
    if (!this.textMessage?.trim()) return;

    this.webrtcService.sendTextMessage(this.textMessage);

    // Add to transcript display
    this.transcripts.push({
      text: this.textMessage,
      timestamp: new Date()
    });

    this.textMessage = '';
  }

  cancelResponse(): void {
    this.webrtcService.cancelResponse();
  }

  toggleTextInput(): void {
    this.showTextInput = !this.showTextInput;
  }

  clearError(): void {
    // Error will be cleared when sessionState updates
  }

  getConnectionStatusText(): string {
    if (this.sessionState.isConnecting) return 'Connessione in corso...';
    if (this.sessionState.isConnected) return 'Connesso';
    return 'Disconnesso';
  }

  trackTranscript(index: number, item: VoiceTranscript): string {
    return `${item.timestamp.getTime()}-${index}`;
  }

  private async loadAudioDevices(): Promise<void> {
    try {
      this.audioDevices = await this.webrtcService.getAudioDevices();

      if (this.audioDevices.length > 0) {
        this.selectedDeviceId = this.audioDevices[0].deviceId;
      }
    } catch (error) {
      console.error('Failed to load audio devices:', error);
    }
  }

  async switchAudioDevice(deviceId: string): Promise<void> {
    this.selectedDeviceId = deviceId;

    if (this.sessionState.isConnected) {
      try {
        await this.webrtcService.switchAudioDevice(deviceId);
        this.snackBar.open('Dispositivo audio cambiato', 'Chiudi', { duration: 2000 });
      } catch (error) {
        this.snackBar.open('Errore nel cambio dispositivo', 'Chiudi', { duration: 3000 });
      }
    }
  }

  onTemperatureChange(event: any): void {
    const value = typeof event === 'number' ? event : event.target?.value || event.value;
    this.configForm.patchValue({ temperature: value });
  }
}