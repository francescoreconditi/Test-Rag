import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subject, takeUntil } from 'rxjs';

import { VoiceChatService, VoiceSession, VoiceMessage } from '../../../core/services/voice-chat.service';

@Component({
  selector: 'app-voice-input',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="voice-input-container">
      <!-- Voice Button -->
      <button
        mat-fab
        [color]="getButtonColor()"
        [class]="getButtonClass()"
        (click)="toggleVoiceInput()"
        [disabled]="isProcessing"
        matTooltip="{{ getTooltipText() }}"
        matTooltipPosition="left">

        <mat-spinner
          *ngIf="isProcessing"
          diameter="24"
          color="accent">
        </mat-spinner>

        <mat-icon *ngIf="!isProcessing">
          {{ getButtonIcon() }}
        </mat-icon>
      </button>

      <!-- Voice Status Indicator -->
      <div class="voice-status" *ngIf="session.isActive">
        <div class="status-indicator" [class.recording]="session.isRecording" [class.playing]="session.isPlaying">
          <span class="status-text">{{ getStatusText() }}</span>
        </div>
      </div>

      <!-- Voice Messages Preview (optional) -->
      <div class="voice-messages" *ngIf="showMessages && session.messages.length > 0">
        <div
          class="message"
          *ngFor="let message of getRecentMessages()"
          [class.user]="message.type === 'user'"
          [class.assistant]="message.type === 'assistant'">
          <div class="message-content">
            <mat-icon class="message-icon">
              {{ message.type === 'user' ? 'person' : 'smart_toy' }}
            </mat-icon>
            <span class="message-text">{{ message.content }}</span>
          </div>
          <div class="message-time">
            {{ formatTime(message.timestamp) }}
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .voice-input-container {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      width: 100%;
      max-width: 100%;
    }

    .voice-button {
      transition: all 0.3s ease;
      box-shadow: 0 4px 12px rgba(103, 126, 234, 0.3);

      &.recording {
        background-color: #f44336 !important;
        animation: pulse 1.5s infinite;
      }

      &.active {
        background-color: #4caf50 !important;
      }

      &:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 16px rgba(103, 126, 234, 0.4);
      }
    }

    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.05); }
      100% { transform: scale(1); }
    }

    .voice-status {
      position: absolute;
      top: -40px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10;
    }

    .status-indicator {
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 0.8rem;
      white-space: nowrap;
      backdrop-filter: blur(4px);

      &.recording {
        background: rgba(244, 67, 54, 0.9);
        animation: pulse 1s infinite;
      }

      &.playing {
        background: rgba(76, 175, 80, 0.9);
      }
    }

    .status-text {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .voice-messages {
      position: relative;
      top: 0;
      left: 0;
      transform: none;
      width: 100%;
      max-width: 100%;
      min-width: unset;
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      border: 1px solid #e0e0e0;
      max-height: 400px;
      overflow-y: auto;
      overflow-x: hidden;
      z-index: 20;
      margin-top: 16px;
      word-wrap: break-word;
    }

    .message {
      padding: 12px 16px;
      border-bottom: 1px solid #f5f5f5;

      &:last-child {
        border-bottom: none;
      }

      &.user {
        background: #f8f9ff;
      }

      &.assistant {
        background: #f0f8f0;
      }
    }

    .message-content {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 4px;
    }

    .message-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #666;
      flex-shrink: 0;
      margin-top: 2px;
    }

    .message-text {
      font-size: 0.9rem;
      line-height: 1.4;
      flex: 1;
      word-wrap: break-word;
      word-break: break-word;
      white-space: pre-wrap;
      overflow-wrap: break-word;
      hyphens: auto;
    }

    .message-time {
      font-size: 0.7rem;
      color: #999;
      text-align: right;
    }

    /* Dark theme support */
    :host-context(.dark-theme) .voice-messages,
    :host-context([data-theme="dark"]) .voice-messages {
      background: #2a2a2a;
      border-color: #444;
      color: white;
    }

    :host-context(.dark-theme) .message,
    :host-context([data-theme="dark"]) .message {
      border-color: #444;
    }

    :host-context(.dark-theme) .message.user,
    :host-context([data-theme="dark"]) .message.user {
      background: #1a1a2e;
    }

    :host-context(.dark-theme) .message.assistant,
    :host-context([data-theme="dark"]) .message.assistant {
      background: #0d1b0d;
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
      .voice-messages {
        width: 100%;
        max-width: 100%;
        margin-top: 12px;
      }

      .message {
        padding: 10px 12px;
      }

      .message-text {
        font-size: 0.85rem;
      }
    }
  `]
})
export class VoiceInputComponent implements OnInit, OnDestroy {
  @Input() disabled: boolean = false;
  @Input() showMessages: boolean = true;
  @Output() transcriptReceived = new EventEmitter<string>();
  @Output() voiceSessionStateChanged = new EventEmitter<boolean>();
  @Output() sessionStarted = new EventEmitter<void>();
  @Output() sessionEnded = new EventEmitter<void>();

  session: VoiceSession = {
    isActive: false,
    isRecording: false,
    isPlaying: false,
    messages: []
  };

  isProcessing = false;

  private destroy$ = new Subject<void>();

  constructor(
    public voiceChatService: VoiceChatService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    // Subscribe to voice session changes
    this.voiceChatService.session$
      .pipe(takeUntil(this.destroy$))
      .subscribe(session => {
        this.session = session;
        this.voiceSessionStateChanged.emit(session.isActive);
      });

    // Subscribe to voice errors
    this.voiceChatService.error$
      .pipe(takeUntil(this.destroy$))
      .subscribe(error => {
        this.snackBar.open(error, 'Chiudi', {
          duration: 5000,
          panelClass: ['error-snack']
        });
        this.isProcessing = false;
      });

    // Listen for new messages to emit transcript and log assistant responses
    this.voiceChatService.session$
      .pipe(takeUntil(this.destroy$))
      .subscribe(session => {
        const lastMessage = session.messages[session.messages.length - 1];
        if (lastMessage) {
          console.log('🎯 New message added to session:', lastMessage);

          if (lastMessage.type === 'assistant') {
            console.log('🤖 Assistant response received:', lastMessage.content);
          }
        }
      });

    // Listen directly to transcript$ for voice input
    this.voiceChatService.transcript$
      .pipe(takeUntil(this.destroy$))
      .subscribe(transcript => {
        console.log('🎙️ Transcript received in component:', transcript);
        this.transcriptReceived.emit(transcript);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();

    // Clean up voice session if active
    if (this.session.isActive) {
      this.voiceChatService.stopVoiceSession();
    }
  }

  async toggleVoiceInput(): Promise<void> {
    console.log('🎤 toggleVoiceInput() called', {
      disabled: this.disabled,
      isProcessing: this.isProcessing,
      sessionState: this.session
    });

    if (this.disabled || this.isProcessing) {
      console.log('⚠️ Voice input disabled or processing');
      return;
    }

    this.isProcessing = true;

    try {
      if (!this.session.isActive) {
        console.log('🚀 Starting voice session...');
        // Start voice session
        await this.voiceChatService.startVoiceSession();
        console.log('✅ Voice session started successfully');
        this.sessionStarted.emit();
        this.snackBar.open('Sessione vocale avviata', 'Chiudi', {
          duration: 2000,
          panelClass: ['success-snack']
        });
      } else if (this.session.isRecording) {
        console.log('🔴 Stopping recording...');
        // Stop recording
        await this.voiceChatService.stopRecording();
        console.log('✅ Recording stopped');
      } else {
        console.log('🎙️ Starting recording...');
        // Start recording
        await this.voiceChatService.startRecording();
        console.log('✅ Recording started');
      }
    } catch (error) {
      console.error('❌ Voice input error:', error);
      this.snackBar.open('Errore nell\'input vocale', 'Chiudi', {
        duration: 3000,
        panelClass: ['error-snack']
      });
    } finally {
      this.isProcessing = false;
      console.log('🏁 toggleVoiceInput() completed');
    }
  }

  async stopVoiceSession(): Promise<void> {
    if (this.session.isActive) {
      this.isProcessing = true;
      try {
        await this.voiceChatService.stopVoiceSession();
        this.sessionEnded.emit();
        this.snackBar.open('Sessione vocale terminata', 'Chiudi', {
          duration: 2000
        });
      } catch (error) {
        console.error('Stop voice session error:', error);
      } finally {
        this.isProcessing = false;
      }
    }
  }

  sendTextMessage(message: string): void {
    if (this.session.isActive) {
      this.voiceChatService.sendTextMessage(message);
    }
  }

  getButtonColor(): string {
    if (this.session.isRecording) return 'warn';
    if (this.session.isActive) return 'accent';
    return 'primary';
  }

  getButtonClass(): string {
    let classes = 'voice-button';
    if (this.session.isRecording) classes += ' recording';
    if (this.session.isActive) classes += ' active';
    return classes;
  }

  getButtonIcon(): string {
    if (this.session.isRecording) return 'stop';
    if (this.session.isActive) return 'mic';
    return 'mic_none';
  }

  getTooltipText(): string {
    if (this.disabled) return 'Input vocale non disponibile';
    if (this.isProcessing) return 'Elaborazione in corso...';
    if (this.session.isRecording) return 'Ferma registrazione';
    if (this.session.isActive) return 'Inizia a parlare';
    return 'Avvia input vocale';
  }

  getStatusText(): string {
    if (this.session.isRecording) return '🔴 Registrando...';
    if (this.session.isPlaying) return '🔊 Riproduzione...';
    if (this.session.isActive) return '🎤 Pronto';
    return '';
  }

  getRecentMessages(): VoiceMessage[] {
    const recentMessages = this.session.messages.slice(-3); // Show last 3 messages
    console.log('📋 getRecentMessages called:', {
      showMessages: this.showMessages,
      totalMessages: this.session.messages.length,
      recentMessages: recentMessages
    });
    return recentMessages;
  }

  formatTime(timestamp: Date): string {
    return new Intl.DateTimeFormat('it-IT', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(timestamp);
  }

  // Programmatic methods for integration
  clearMessages(): void {
    this.voiceChatService.clearMessages();
  }

  isVoiceAvailable(): boolean {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }
}