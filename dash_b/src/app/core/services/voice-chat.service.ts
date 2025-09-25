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

  private sessionSubject = new BehaviorSubject<VoiceSession>({
    isActive: false,
    isRecording: false,
    isPlaying: false,
    messages: []
  });

  private errorSubject = new Subject<string>();

  public session$ = this.sessionSubject.asObservable();
  public error$ = this.errorSubject.asObservable();

  // Production WebSocket server
  private readonly BACKEND_WS_URL = 'ws://localhost:8000/voice/realtime';
  private clientId: string = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

  constructor() {
    // Client ID initialized above
  }

  async startVoiceSession(): Promise<void> {
    try {
      console.log('🔍 VoiceChatService.startVoiceSession() called');
      console.log('🔍 Starting OpenAI Realtime voice session via backend proxy...');

      console.log('🎤 Requesting microphone permission...');
      // Request microphone permission
      await this.requestMicrophonePermission();
      console.log('✅ Microphone permission granted');

      console.log('🔌 Connecting to backend WebSocket proxy...');
      // Connect to backend WebSocket proxy
      await this.connectToBackendProxy();
      console.log('✅ Backend WebSocket proxy connected');

      console.log('📊 Updating session state to active...');
      // Update session state
      this.updateSession({ isActive: true });
      console.log('✅ Voice session started successfully');

    } catch (error) {
      console.error('❌ Error in startVoiceSession:', error);
      this.handleError(`Errore avvio sessione vocale: ${error}`);
      throw error;
    }
  }

  // Microphone testing removed - handled by MediaRecorder setup

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
    if (this.sessionSubject.value.isRecording || !this.audioStream) {
      return;
    }

    try {
      console.log('🎙️ Starting audio recording...');

      // Setup MediaRecorder to capture audio for OpenAI
      // Use a format closer to PCM16 requirements
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=pcm') ?
        'audio/webm;codecs=pcm' :
        (MediaRecorder.isTypeSupported('audio/wav') ? 'audio/wav' : 'audio/webm');

      console.log('🎵 Using MIME type:', mimeType);

      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: mimeType
      });

      let audioChunks: Blob[] = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log('🎵 Audio chunk received:', event.data.size, 'bytes');
          audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        if (audioChunks.length > 0) {
          const audioBlob = new Blob(audioChunks, { type: mimeType });
          console.log('🎵 Final audio blob:', audioBlob.size, 'bytes');
          this.sendAudioToBackend(audioBlob);
          audioChunks = [];
        }
      };

      // Start recording - collect audio for minimum 1 second chunks
      this.mediaRecorder.start(1000); // Collect 1 second chunks minimum
      this.updateSession({ isRecording: true });

    } catch (error) {
      this.handleError(`Errore avvio registrazione: ${error}`);
      this.updateSession({ isRecording: false });
    }
  }

  async stopRecording(): Promise<void> {
    if (!this.mediaRecorder || !this.sessionSubject.value.isRecording) {
      return;
    }

    try {
      console.log('🔴 Stopping audio recording...');

      if (this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop(); // This will trigger onstop which sends the audio
      }

      this.updateSession({ isRecording: false });
    } catch (error) {
      this.handleError(`Errore stop registrazione: ${error}`);
    }
  }

  sendTextMessage(message: string): void {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      // Send text message to backend
      this.websocket.send(JSON.stringify({
        type: 'send_text',
        text: message
      }));
    } else {
      this.handleError('WebSocket connection not available');
    }
  }

  private async sendAudioToBackend(audioBlob: Blob): Promise<void> {
    console.log('🎵 Processing audio blob for OpenAI:', audioBlob.size, 'bytes', audioBlob.type);

    try {
      // Convert audio blob to PCM16 format for OpenAI
      const pcm16Audio = await this.convertToPCM16(audioBlob);
      console.log('🎵 Converted to PCM16:', pcm16Audio.length, 'bytes');

      // Convert to base64 efficiently using chunks to avoid stack overflow
      const chunkSize = 8192;
      let binaryString = '';
      for (let i = 0; i < pcm16Audio.length; i += chunkSize) {
        const chunk = pcm16Audio.slice(i, i + chunkSize);
        binaryString += String.fromCharCode.apply(null, Array.from(chunk));
      }
      const base64Audio = btoa(binaryString);
      console.log('🎵 Sending base64 audio to backend:', base64Audio.length, 'chars');

      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        // Send the audio data
        this.websocket.send(JSON.stringify({
          type: 'send_audio',
          audio: base64Audio
        }));

        // Send commit signal immediately - backend will handle timing
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          console.log('🎵 Committing audio buffer...');
          this.websocket.send(JSON.stringify({
            type: 'commit_audio'
          }));
        }
      }
    } catch (error) {
      console.error('❌ Audio conversion error:', error);
      this.handleError(`Errore conversione audio: ${error}`);
    }
  }

  private async convertToPCM16(audioBlob: Blob): Promise<Uint8Array> {
    // Create audio context for conversion
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
      sampleRate: 24000 // OpenAI requires 24kHz
    });

    try {
      // Convert blob to array buffer
      const arrayBuffer = await audioBlob.arrayBuffer();

      // Decode audio data
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      // Get mono channel (average if stereo)
      let audioData: Float32Array;
      if (audioBuffer.numberOfChannels === 1) {
        audioData = audioBuffer.getChannelData(0);
      } else {
        // Convert stereo to mono by averaging channels
        const left = audioBuffer.getChannelData(0);
        const right = audioBuffer.getChannelData(1);
        audioData = new Float32Array(audioBuffer.length);
        for (let i = 0; i < audioBuffer.length; i++) {
          audioData[i] = (left[i] + right[i]) / 2;
        }
      }

      // Convert float32 to int16 (PCM16)
      const pcm16 = new Int16Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        // Clamp to [-1, 1] and convert to 16-bit integer
        const sample = Math.max(-1, Math.min(1, audioData[i]));
        pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      }

      // Convert to Uint8Array (little-endian)
      const bytes = new Uint8Array(pcm16.length * 2);
      for (let i = 0; i < pcm16.length; i++) {
        bytes[i * 2] = pcm16[i] & 0xFF;
        bytes[i * 2 + 1] = (pcm16[i] >> 8) & 0xFF;
      }

      console.log(`🎵 PCM16 conversion: ${audioBuffer.length} samples -> ${bytes.length} bytes at ${audioBuffer.sampleRate}Hz`);
      return bytes;

    } finally {
      audioContext.close();
    }
  }

  private async requestMicrophonePermission(): Promise<void> {
    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: 24000 }, // OpenAI prefers 24kHz
          channelCount: { exact: 1 }, // Mono audio
          sampleSize: { ideal: 16 } // 16-bit depth
        }
      });
    } catch (error) {
      throw new Error('Accesso al microfono negato. Abilita i permessi per il microfono.');
    }
  }

  private async connectToBackendProxy(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${this.BACKEND_WS_URL}/${this.clientId}`;
        console.log('🔌 connectToBackendProxy() called');
        console.log('🔌 Backend WS URL template:', this.BACKEND_WS_URL);
        console.log('🔌 Client ID:', this.clientId);
        console.log('🔌 Full WebSocket URL:', wsUrl);
        console.log('🔌 Creating WebSocket connection...');

        this.websocket = new WebSocket(wsUrl);
        console.log('🔌 WebSocket object created:', this.websocket);

        this.websocket.onopen = () => {
          console.log('✅ WebSocket ONOPEN event triggered');
          console.log('✅ Connected to backend WebSocket proxy');
          resolve();
        };

        this.websocket.onmessage = (event) => {
          console.log('📨 WebSocket ONMESSAGE event:', event.data);
          try {
            const data = JSON.parse(event.data);
            this.handleBackendMessage(data);
          } catch (error) {
            console.error('❌ Error parsing backend message:', error);
          }
        };

        this.websocket.onerror = (error) => {
          console.error('❌ WebSocket ONERROR event:', error);
          console.error('❌ WebSocket proxy error details:', {
            readyState: this.websocket?.readyState,
            url: wsUrl,
            error: error
          });
          reject(new Error('Errore connessione al proxy vocale'));
        };

        this.websocket.onclose = (event) => {
          console.log('🔌 WebSocket ONCLOSE event:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });
          console.log('🔌 WebSocket proxy connection closed');
          this.updateSession({ isActive: false, isRecording: false });
        };

        console.log('🔌 WebSocket event handlers configured');

      } catch (error) {
        console.error('❌ Exception in connectToBackendProxy:', error);
        reject(error);
      }
    });
  }

  private handleBackendMessage(data: any): void {
    const messageType = data.type;
    console.log('📨 Backend message:', messageType, data);

    switch (messageType) {
      case 'connection_established':
        console.log('🎉 WebSocket connection established');
        break;

      case 'openai_connected':
        console.log('🤖 OpenAI Realtime API connected:', data.message);
        break;

      case 'session_created':
        console.log('🆔 OpenAI session created:', data.session_id);
        break;

      case 'user_transcript':
        // User speech transcribed
        const userMessage: VoiceMessage = {
          id: this.generateId(),
          type: 'user',
          content: data.transcript,
          timestamp: new Date()
        };
        this.addMessage(userMessage);
        break;

      case 'assistant_response':
        // Assistant response (text or audio transcript)
        if (!data.is_delta) {
          // Final response
          const assistantMessage: VoiceMessage = {
            id: this.generateId(),
            type: 'assistant',
            content: data.response,
            timestamp: new Date()
          };
          this.addMessage(assistantMessage);
        }
        break;

      case 'audio_response':
        // Assistant audio response
        if (data.audio) {
          this.playAudioResponse(data.audio);
        }
        break;

      case 'error':
        this.handleError(data.error);
        break;

      case 'pong':
        // Keep-alive response
        break;

      default:
        console.log('📨 Unhandled backend message:', messageType);
    }
  }

  private playAudioResponse(audioBase64: string): void {
    try {
      // Convert base64 to audio and play
      const audioData = atob(audioBase64);
      const audioBuffer = new ArrayBuffer(audioData.length);
      const view = new Uint8Array(audioBuffer);

      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
      }

      // Create audio blob and play
      const blob = new Blob([audioBuffer], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);

      audio.play().then(() => {
        this.updateSession({ isPlaying: true });
      }).catch((error) => {
        console.error('❌ Audio playback error:', error);
      });

      audio.onended = () => {
        this.updateSession({ isPlaying: false });
        URL.revokeObjectURL(audioUrl);
      };

    } catch (error) {
      console.error('❌ Audio processing error:', error);
    }
  }

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

  // Speech Recognition methods removed - now using OpenAI Realtime API via WebSocket proxy

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