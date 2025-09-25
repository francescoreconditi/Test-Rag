import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject, fromEvent } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface VoiceMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioData?: ArrayBuffer;
}

export interface VoiceSession {
  isActive: boolean;
  isRecording: boolean;
  isPlaying: boolean;
  messages: VoiceMessage[];
}

@Injectable({
  providedIn: 'root'
})
export class VoiceChatService {
  private websocket: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private audioStream: MediaStream | null = null;
  private speechRecognition: any = null;

  private sessionSubject = new BehaviorSubject<VoiceSession>({
    isActive: false,
    isRecording: false,
    isPlaying: false,
    messages: []
  });

  private errorSubject = new Subject<string>();

  public session$ = this.sessionSubject.asObservable();
  public error$ = this.errorSubject.asObservable();

  private readonly OPENAI_REALTIME_URL = 'wss://api.openai.com/v1/realtime';
  private readonly OPENAI_API_KEY = environment.openaiApiKey;

  constructor() {}

  async startVoiceSession(): Promise<void> {
    try {
      // Test microphone access first
      console.log('🔍 Testing microphone access...');
      await this.testMicrophoneAccess();

      // Request microphone permission
      await this.requestMicrophonePermission();

      // Connect to Speech API
      await this.connectToRealtimeAPI();

      // Update session state
      this.updateSession({ isActive: true });

    } catch (error) {
      this.handleError(`Errore avvio sessione vocale: ${error}`);
    }
  }

  private async testMicrophoneAccess(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ Microphone access granted');

      // Test if we can get audio levels
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const microphone = audioContext.createMediaStreamSource(stream);

      microphone.connect(analyser);
      analyser.fftSize = 256;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      // Test for 2 seconds
      let testCount = 0;
      const testInterval = setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
        console.log(`🎵 Audio level test ${testCount + 1}/20: ${average.toFixed(2)}`);

        testCount++;
        if (testCount >= 20) {
          clearInterval(testInterval);
          audioContext.close();
          console.log('🎯 Microphone test completed');
        }
      }, 100);

      // Stop the stream after test
      setTimeout(() => {
        stream.getTracks().forEach(track => track.stop());
      }, 2000);

    } catch (error) {
      console.error('❌ Microphone test failed:', error);
      throw error;
    }
  }

  async stopVoiceSession(): Promise<void> {
    try {
      // Stop recording if active
      if (this.sessionSubject.value.isRecording) {
        await this.stopRecording();
      }

      // Close WebSocket connection
      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }

      // Stop audio stream
      if (this.audioStream) {
        this.audioStream.getTracks().forEach(track => track.stop());
        this.audioStream = null;
      }

      // Close audio context
      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }

      // Reset session state
      this.updateSession({
        isActive: false,
        isRecording: false,
        isPlaying: false
      });

    } catch (error) {
      this.handleError(`Errore chiusura sessione vocale: ${error}`);
    }
  }

  async startRecording(): Promise<void> {
    if (this.sessionSubject.value.isRecording || !this.speechRecognition) {
      return;
    }

    try {
      console.log('Starting speech recognition...');
      this.updateSession({ isRecording: true });
      this.speechRecognition.start();

    } catch (error) {
      this.handleError(`Errore avvio registrazione: ${error}`);
      this.updateSession({ isRecording: false });
    }
  }

  async stopRecording(): Promise<void> {
    if (!this.speechRecognition || !this.sessionSubject.value.isRecording) {
      return;
    }

    try {
      console.log('Stopping speech recognition...');
      this.speechRecognition.stop();
      this.updateSession({ isRecording: false });
    } catch (error) {
      this.handleError(`Errore stop registrazione: ${error}`);
    }
  }

  sendTextMessage(message: string): void {
    // For Web Speech API fallback, we just add the message
    const userMessage: VoiceMessage = {
      id: this.generateId(),
      type: 'user',
      content: message,
      timestamp: new Date()
    };

    this.addMessage(userMessage);
  }

  private async requestMicrophonePermission(): Promise<void> {
    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 24000
        }
      });
    } catch (error) {
      throw new Error('Accesso al microfono negato. Abilita i permessi per il microfono.');
    }
  }

  private async connectToRealtimeAPI(): Promise<void> {
    return new Promise((resolve, reject) => {
      // For now, we'll use browser's Web Speech API as fallback
      // OpenAI Realtime API requires server-side WebSocket proxy for proper authentication
      console.log('Using Web Speech API fallback for voice recognition');

      // Check if Web Speech API is available
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        reject(new Error('Speech recognition non supportato in questo browser'));
        return;
      }

      // Initialize Web Speech API for fallback
      this.initializeSpeechRecognition();
      resolve();
    });
  }

  // Removed OpenAI Realtime API methods for now - using Web Speech API fallback

  private addMessage(message: VoiceMessage): void {
    const currentSession = this.sessionSubject.value;
    const updatedMessages = [...currentSession.messages, message];
    this.updateSession({ messages: updatedMessages });
  }

  // updateLastAssistantMessage removed - not needed for Web Speech API

  private updateSession(updates: Partial<VoiceSession>): void {
    const currentSession = this.sessionSubject.value;
    this.sessionSubject.next({ ...currentSession, ...updates });
  }

  private handleError(error: string): void {
    console.error(error);
    this.errorSubject.next(error);
  }

  private initializeSpeechRecognition(): void {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error('Speech Recognition API not available');
      return;
    }

    this.speechRecognition = new SpeechRecognition();
    this.speechRecognition.continuous = true;  // Changed to true for continuous listening
    this.speechRecognition.interimResults = true;
    this.speechRecognition.lang = 'it-IT';
    this.speechRecognition.maxAlternatives = 1;

    this.speechRecognition.onstart = () => {
      console.log('🎤 Speech recognition started');
    };

    this.speechRecognition.onresult = (event: any) => {
      console.log('📝 Speech recognition result event:', event);

      let transcript = '';
      let isFinal = false;

      // Process all results
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        transcript += result[0].transcript;

        if (result.isFinal) {
          isFinal = true;
        }

        console.log(`Result ${i}: "${result[0].transcript}" (confidence: ${result[0].confidence}, final: ${result.isFinal})`);
      }

      console.log('Full transcript:', transcript, 'Final:', isFinal);

      if (transcript.trim()) {
        if (isFinal) {
          console.log('✅ Final transcript received:', transcript);

          // Create user message
          const userMessage: VoiceMessage = {
            id: this.generateId(),
            type: 'user',
            content: transcript.trim(),
            timestamp: new Date()
          };

          this.addMessage(userMessage);

          // Don't stop automatically - let user decide when to stop
          // this.updateSession({ isRecording: false });
        } else {
          console.log('⏳ Interim transcript:', transcript);
          // You could show interim results in the UI if needed
        }
      }
    };

    this.speechRecognition.onerror = (event: any) => {
      console.error('❌ Speech recognition error:', event.error, event);

      let errorMessage = 'Errore riconoscimento vocale';
      switch (event.error) {
        case 'no-speech':
          errorMessage = 'Nessun parlato rilevato. Prova a parlare più forte.';
          break;
        case 'audio-capture':
          errorMessage = 'Impossibile accedere al microfono.';
          break;
        case 'not-allowed':
          errorMessage = 'Permesso microfono negato.';
          break;
        case 'network':
          errorMessage = 'Errore di rete durante il riconoscimento vocale.';
          break;
        default:
          errorMessage = `Errore riconoscimento vocale: ${event.error}`;
      }

      this.handleError(errorMessage);
      this.updateSession({ isRecording: false });
    };

    this.speechRecognition.onend = () => {
      console.log('🔴 Speech recognition ended');
      this.updateSession({ isRecording: false });
    };

    this.speechRecognition.onnomatch = (event: any) => {
      console.log('🤷 No speech matches found');
    };

    this.speechRecognition.onspeechstart = () => {
      console.log('🗣️ Speech detected');
    };

    this.speechRecognition.onspeechend = () => {
      console.log('🔇 Speech ended');
    };
  }

  private generateId(): string {
    return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // Get current session state
  getCurrentSession(): VoiceSession {
    return this.sessionSubject.value;
  }

  // Clear messages
  clearMessages(): void {
    this.updateSession({ messages: [] });
  }
}