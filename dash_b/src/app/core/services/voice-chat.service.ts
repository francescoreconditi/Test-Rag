import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';

export interface VoiceMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioUrl?: string;
}

export interface VoiceSession {
  isActive: boolean;
  isRecording: boolean;
  isPlaying: boolean;
  messages: VoiceMessage[];
}

// Web Speech API interfaces
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: ((event: Event) => void) | null;
  onend: ((event: Event) => void) | null;
  onerror: ((event: any) => void) | null;
  onresult: ((event: any) => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: {
      new(): SpeechRecognition;
    };
    webkitSpeechRecognition: {
      new(): SpeechRecognition;
    };
    SpeechSynthesisUtterance: {
      new(text?: string): SpeechSynthesisUtterance;
    };
  }
}

@Injectable({
  providedIn: 'root'
})
export class VoiceChatService {
  private recognition: SpeechRecognition | null = null;
  private currentTranscript = '';
  private speechSynthesis: SpeechSynthesis | null = null;

  private sessionSubject = new BehaviorSubject<VoiceSession>({
    isActive: false,
    isRecording: false,
    isPlaying: false,
    messages: []
  });

  private errorSubject = new Subject<string>();
  private transcriptSubject = new Subject<string>();

  public session$ = this.sessionSubject.asObservable();
  public error$ = this.errorSubject.asObservable();
  public transcript$ = this.transcriptSubject.asObservable();

  constructor() {
    this.initializeSpeechRecognition();
    this.initializeSpeechSynthesis();
  }

  private initializeSpeechRecognition(): void {
    // Check if speech recognition is supported
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error('Speech Recognition API not supported in this browser');
      this.errorSubject.next('Speech Recognition non supportato in questo browser');
      return;
    }

    this.recognition = new SpeechRecognition();

    if (this.recognition) {
      this.recognition.continuous = false; // Stop after one result
      this.recognition.interimResults = true; // Get interim results
      this.recognition.lang = 'it-IT'; // Italian language

      this.recognition.onstart = () => {
        console.log('🎤 Speech recognition started');
        this.updateSession({ isRecording: true });
      };

      this.recognition.onend = () => {
        console.log('🔴 Speech recognition ended');
        this.updateSession({ isRecording: false });
      };

      this.recognition.onerror = (event: any) => {
      console.error('❌ Speech recognition error:', event.error);
      let errorMessage = 'Errore nel riconoscimento vocale';

      switch (event.error) {
        case 'not-allowed':
          errorMessage = 'Permessi microfoniali necessari';
          break;
        case 'no-speech':
          errorMessage = 'Nessun audio rilevato';
          break;
        case 'audio-capture':
          errorMessage = 'Errore nella cattura audio';
          break;
        case 'network':
          errorMessage = 'Errore di connessione di rete';
          break;
        default:
          errorMessage = `Errore: ${event.error}`;
      }

      this.errorSubject.next(errorMessage);
      this.updateSession({ isRecording: false });
    };

      this.recognition.onresult = (event: any) => {
        let finalTranscript = '';
        let interimTranscript = '';

        // Process all results
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcript = result[0].transcript;

          if (result.isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        // Update current transcript
        this.currentTranscript = finalTranscript || interimTranscript;

        console.log('🎯 Speech result:', {
          final: finalTranscript,
          interim: interimTranscript,
          current: this.currentTranscript
        });

        // If we have a final result, process it
        if (finalTranscript.trim()) {
          this.processFinalTranscript(finalTranscript.trim());
        }
      };
    }
  }

  private processFinalTranscript(transcript: string): void {
    console.log('✅ Final transcript received:', transcript);

    // Just emit the transcript - let the parent component handle message addition
    this.transcriptSubject.next(transcript);

    // Update session state
    this.updateSession({ isRecording: false });
  }

  async startVoiceSession(): Promise<void> {
    if (!this.recognition) {
      throw new Error('Speech Recognition non inizializzato');
    }

    try {
      console.log('🚀 Starting voice session...');
      this.updateSession({
        isActive: true,
        messages: [] // Clear previous messages
      });

    } catch (error) {
      console.error('❌ Failed to start voice session:', error);
      throw error;
    }
  }

  async startRecording(): Promise<void> {
    if (!this.recognition) {
      throw new Error('Speech Recognition non disponibile');
    }

    try {
      console.log('🎙️ Starting recording...');
      this.currentTranscript = '';
      this.recognition.start();
    } catch (error) {
      console.error('❌ Failed to start recording:', error);
      this.errorSubject.next('Impossibile avviare la registrazione');
      throw error;
    }
  }

  async stopRecording(): Promise<void> {
    if (!this.recognition) {
      return;
    }

    try {
      console.log('⏹️ Stopping recording...');
      this.recognition.stop();
    } catch (error) {
      console.error('❌ Failed to stop recording:', error);
    }
  }

  async stopVoiceSession(): Promise<void> {
    try {
      console.log('🛑 Stopping voice session...');

      if (this.recognition) {
        this.recognition.abort();
      }

      this.updateSession({
        isActive: false,
        isRecording: false,
        isPlaying: false
      });

      console.log('✅ Voice session stopped');
    } catch (error) {
      console.error('❌ Failed to stop voice session:', error);
    }
  }

  // Method to add user messages (for displaying conversation)
  addUserMessage(content: string): void {
    const userMessage: VoiceMessage = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: content,
      timestamp: new Date()
    };

    const currentSession = this.sessionSubject.value;
    const updatedMessages = [...currentSession.messages, userMessage];

    this.updateSession({ messages: updatedMessages });
  }

  // Method to add assistant responses (for displaying conversation)
  addAssistantMessage(content: string): void {
    const assistantMessage: VoiceMessage = {
      id: `assistant_${Date.now()}`,
      type: 'assistant',
      content: content,
      timestamp: new Date()
    };

    const currentSession = this.sessionSubject.value;
    const updatedMessages = [...currentSession.messages, assistantMessage];

    this.updateSession({ messages: updatedMessages });
  }

  // For backward compatibility - now just adds to message history
  sendTextMessage(message: string): void {
    console.log('📝 Adding text message to history:', message);

    const textMessage: VoiceMessage = {
      id: `text_${Date.now()}`,
      type: 'user',
      content: message,
      timestamp: new Date()
    };

    const currentSession = this.sessionSubject.value;
    const updatedMessages = [...currentSession.messages, textMessage];

    this.updateSession({ messages: updatedMessages });
  }

  clearMessages(): void {
    this.updateSession({ messages: [] });
  }

  private updateSession(updates: Partial<VoiceSession>): void {
    const currentSession = this.sessionSubject.value;
    const newSession = { ...currentSession, ...updates };
    this.sessionSubject.next(newSession);
  }

  private initializeSpeechSynthesis(): void {
    if ('speechSynthesis' in window) {
      this.speechSynthesis = window.speechSynthesis;
      console.log('🔊 Speech synthesis initialized');
    } else {
      console.error('❌ Speech synthesis not supported');
      this.errorSubject.next('Sintesi vocale non supportata in questo browser');
    }
  }

  // Speak text using text-to-speech
  async speakText(text: string): Promise<void> {
    if (!this.speechSynthesis) {
      console.error('❌ Speech synthesis not available');
      return;
    }

    try {
      // Stop any current speech
      this.speechSynthesis.cancel();

      // Update session state to playing
      this.updateSession({ isPlaying: true });

      // Create utterance
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'it-IT'; // Italian voice
      utterance.rate = 0.9; // Slightly slower
      utterance.pitch = 1.0;
      utterance.volume = 0.8;

      // Event handlers
      utterance.onstart = () => {
        console.log('🔊 Starting speech synthesis');
        this.updateSession({ isPlaying: true });
      };

      utterance.onend = () => {
        console.log('✅ Speech synthesis completed');
        this.updateSession({ isPlaying: false });
      };

      utterance.onerror = (event) => {
        console.error('❌ Speech synthesis error:', event);
        this.updateSession({ isPlaying: false });
        this.errorSubject.next('Errore nella sintesi vocale');
      };

      // Start speaking
      this.speechSynthesis.speak(utterance);

      console.log('🔊 Speaking text:', text.substring(0, 50) + '...');

    } catch (error) {
      console.error('❌ Speech synthesis failed:', error);
      this.updateSession({ isPlaying: false });
      this.errorSubject.next('Impossibile riprodurre la risposta vocale');
    }
  }

  // Stop current speech
  stopSpeaking(): void {
    if (this.speechSynthesis) {
      this.speechSynthesis.cancel();
      this.updateSession({ isPlaying: false });
      console.log('⏹️ Speech synthesis stopped');
    }
  }

  // Check if speech recognition is available
  isSpeechRecognitionSupported(): boolean {
    return !!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition;
  }

  // Check if speech synthesis is available
  isSpeechSynthesisSupported(): boolean {
    return 'speechSynthesis' in window;
  }
}