import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';

// OpenAI Realtime API Events
export interface RealtimeEvent {
  type: string;
  event_id?: string;
  [key: string]: any;
}

export interface SessionConfig {
  model: string;
  modalities: string[];
  instructions: string;
  voice: string;
  input_audio_format: string;
  output_audio_format: string;
  input_audio_transcription?: {
    model: string;
  };
  turn_detection?: {
    type: string;
    threshold?: number;
    prefix_padding_ms?: number;
    silence_duration_ms?: number;
  };
  tools?: any[];
  tool_choice?: string;
  temperature?: number;
  max_response_output_tokens?: number | string;
}

export interface WebRTCSessionState {
  isConnected: boolean;
  isConnecting: boolean;
  isRecording: boolean;
  isSpeaking: boolean;
  sessionId?: string;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class OpenAIWebRTCService {
  private peerConnection: RTCPeerConnection | null = null;
  private dataChannel: RTCDataChannel | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sessionConfig: SessionConfig;
  private eventQueue: RealtimeEvent[] = [];

  // State management
  private sessionStateSubject = new BehaviorSubject<WebRTCSessionState>({
    isConnected: false,
    isConnecting: false,
    isRecording: false,
    isSpeaking: false
  });

  private eventSubject = new Subject<RealtimeEvent>();
  private audioDataSubject = new Subject<ArrayBuffer>();
  private transcriptSubject = new Subject<string>();
  private errorSubject = new Subject<string>();

  // Observables
  public sessionState$ = this.sessionStateSubject.asObservable();
  public events$ = this.eventSubject.asObservable();
  public audioData$ = this.audioDataSubject.asObservable();
  public transcript$ = this.transcriptSubject.asObservable();
  public error$ = this.errorSubject.asObservable();

  // Default session configuration
  constructor() {
    this.sessionConfig = {
      model: 'gpt-4o-realtime-preview-2024-12-17',
      modalities: ['text', 'audio'],
      instructions: 'Sei un assistente AI specializzato nell\'analisi di documenti finanziari. Rispondi in italiano con un tono professionale e preciso.',
      voice: 'alloy',
      input_audio_format: 'pcm16',
      output_audio_format: 'pcm16',
      input_audio_transcription: {
        model: 'whisper-1'
      },
      turn_detection: {
        type: 'server_vad',
        threshold: 0.5,
        prefix_padding_ms: 300,
        silence_duration_ms: 500
      },
      temperature: 0.7,
      max_response_output_tokens: 4096
    };
  }

  async connectToOpenAI(apiKey: string): Promise<void> {
    try {
      this.updateSessionState({ isConnecting: true, error: undefined });

      // Validate and clean API key
      const cleanApiKey = apiKey.trim();
      if (!cleanApiKey || !cleanApiKey.startsWith('sk-')) {
        throw new Error('API key non valida. Deve iniziare con "sk-"');
      }

      // Ensure API key contains only ASCII characters
      if (!/^[\x00-\x7F]*$/.test(cleanApiKey)) {
        throw new Error('API key contiene caratteri non validi. Usa solo caratteri ASCII.');
      }

      // Initialize WebRTC peer connection with proper ICE servers
      this.peerConnection = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      });

      this.setupPeerConnectionHandlers();

      // Create data channel for events
      this.dataChannel = this.peerConnection.createDataChannel('oai-events', {
        ordered: true
      });
      this.setupDataChannelHandlers();

      // Get user media for audio input
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
          channelCount: 1
        }
      });

      // Add audio track to peer connection
      this.mediaStream.getAudioTracks().forEach(track => {
        this.peerConnection!.addTrack(track, this.mediaStream!);
      });

      // Setup real-time audio streaming
      this.setupAudioRecording();

      // Create and set local description
      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);

      console.log('🎙️ Creating OpenAI WebRTC session...');

      // Create WebRTC call using the correct OpenAI API endpoint with SDP format
      const webrtcResponse = await fetch(`https://api.openai.com/v1/realtime?model=${this.sessionConfig.model}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${cleanApiKey}`,
          'Content-Type': 'application/sdp'
        },
        body: offer.sdp
      });

      if (!webrtcResponse.ok) {
        const errorData = await webrtcResponse.text();
        throw new Error(`Failed to establish WebRTC connection: ${webrtcResponse.status} ${webrtcResponse.statusText} - ${errorData}`);
      }

      // OpenAI returns SDP response directly
      const answerSdp = await webrtcResponse.text();
      console.log('✅ OpenAI WebRTC call established');

      // Set remote description from OpenAI SDP response
      if (answerSdp && answerSdp.trim()) {
        const remoteDesc = new RTCSessionDescription({
          type: 'answer',
          sdp: answerSdp
        });
        await this.peerConnection.setRemoteDescription(remoteDesc);
        console.log('🔗 WebRTC peer connection established');
      } else {
        throw new Error('Invalid WebRTC answer from OpenAI');
      }

      console.log('🎙️ WebRTC connection established with OpenAI successfully');
      this.updateSessionState({
        isConnected: true,
        isConnecting: false,
        sessionId: `webrtc-${Date.now()}`
      });

      // Wait for data channel to be ready before sending configuration
      if (this.dataChannel && this.dataChannel.readyState === 'open') {
        this.sendSessionUpdate();
      } else {
        // Listen for data channel to open
        this.peerConnection.ondatachannel = (event) => {
          if (event.channel.label === 'oai-events') {
            this.dataChannel = event.channel;
            this.setupDataChannelHandlers();
            // Send session configuration once channel is ready
            setTimeout(() => this.sendSessionUpdate(), 100);
          }
        };
      }

    } catch (error) {
      console.error('❌ Failed to connect to OpenAI WebRTC:', error);
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      this.updateSessionState({
        isConnecting: false,
        isConnected: false,
        error: errorMessage
      });
      this.errorSubject.next(errorMessage);
      throw error;
    }
  }

  private sendSessionUpdate(): void {
    this.sendEvent({
      type: 'session.update',
      session: this.sessionConfig
    });
  }

  private setupDataChannelHandlers(): void {
    if (!this.dataChannel) return;

    this.dataChannel.onopen = () => {
      console.log('🔗 WebRTC data channel opened');
      this.flushEventQueue();
    };

    this.dataChannel.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleRealtimeEvent(data);
      } catch (error) {
        console.error('❌ Failed to parse WebRTC message:', error);
      }
    };

    this.dataChannel.onerror = (error) => {
      console.error('❌ WebRTC data channel error:', error);
      this.errorSubject.next('Data channel error');
    };

    this.dataChannel.onclose = () => {
      console.log('🔌 WebRTC data channel closed');
      this.updateSessionState({ isConnected: false });
    };
  }

  private setupPeerConnectionHandlers(): void {
    if (!this.peerConnection) return;

    this.peerConnection.oniceconnectionstatechange = () => {
      const state = this.peerConnection!.iceConnectionState;
      console.log('🧊 ICE connection state:', state);

      if (state === 'connected') {
        console.log('✅ WebRTC peer connection established');
      } else if (state === 'failed' || state === 'disconnected') {
        this.updateSessionState({ isConnected: false });
        this.errorSubject.next('WebRTC connection lost');
      }
    };

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('🧊 New ICE candidate:', event.candidate);
      } else {
        console.log('🧊 ICE gathering complete');
      }
    };

    this.peerConnection.ontrack = (event) => {
      console.log('🎵 Received remote audio track from OpenAI');
      const [remoteStream] = event.streams;
      this.playAudioStream(remoteStream);
    };

    this.peerConnection.ondatachannel = (event) => {
      const channel = event.channel;
      console.log('📡 Received data channel from OpenAI:', channel.label);

      if (channel.label === 'oai-events') {
        this.dataChannel = channel;
        this.setupDataChannelHandlers();

        // Send session configuration once channel is ready
        channel.onopen = () => {
          console.log('📡 Data channel opened');
          setTimeout(() => this.sendSessionUpdate(), 100);
        };
      }
    };

    this.peerConnection.onconnectionstatechange = () => {
      const state = this.peerConnection!.connectionState;
      console.log('🔗 WebRTC connection state:', state);

      if (state === 'connected') {
        console.log('🎉 WebRTC fully connected to OpenAI');
      } else if (state === 'failed' || state === 'disconnected') {
        this.updateSessionState({ isConnected: false });
        this.errorSubject.next('WebRTC connection failed');
      }
    };
  }

  private handleRealtimeEvent(event: RealtimeEvent): void {
    console.log('📨 Received OpenAI event:', event.type);

    switch (event.type) {
      case 'session.created':
        console.log('✅ Session created:', event['session']);
        break;

      case 'session.updated':
        console.log('🔄 Session updated:', event['session']);
        break;

      case 'input_audio_buffer.speech_started':
        this.updateSessionState({ isRecording: true });
        break;

      case 'input_audio_buffer.speech_stopped':
        this.updateSessionState({ isRecording: false });
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (event['transcript']) {
          this.transcriptSubject.next(event['transcript']);
        }
        break;

      case 'response.audio.delta':
        if (event['delta']) {
          // Convert base64 audio to ArrayBuffer
          const audioData = Uint8Array.from(atob(event['delta']), c => c.charCodeAt(0));
          this.audioDataSubject.next(audioData.buffer);
        }
        break;

      case 'response.audio.done':
        this.updateSessionState({ isSpeaking: false });
        break;

      case 'response.audio_transcript.delta':
        if (event['delta']) {
          this.transcriptSubject.next(event['delta']);
        }
        break;

      case 'error':
        console.error('❌ OpenAI API error:', event['error']);
        this.errorSubject.next(event['error']?.message || 'API error');
        break;

      default:
        console.log('📋 Unhandled event:', event.type);
    }

    // Emit all events for external handling
    this.eventSubject.next(event);
  }

  private playAudioStream(stream: MediaStream): void {
    const audioElement = new Audio();
    audioElement.srcObject = stream;
    audioElement.autoplay = true;

    audioElement.onplay = () => {
      this.updateSessionState({ isSpeaking: true });
    };

    audioElement.onended = () => {
      this.updateSessionState({ isSpeaking: false });
    };
  }

  sendEvent(event: RealtimeEvent): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      console.log('📋 Queuing event (data channel not ready):', event.type);
      this.eventQueue.push(event);
      return;
    }

    try {
      const eventData = JSON.stringify(event);
      this.dataChannel.send(eventData);
      console.log('📤 Sent event:', event.type);
    } catch (error) {
      console.error('❌ Failed to send event:', error);
      this.errorSubject.next('Failed to send event');
    }
  }

  private flushEventQueue(): void {
    if (!this.dataChannel || this.dataChannel.readyState !== 'open') {
      return;
    }

    console.log(`📤 Flushing ${this.eventQueue.length} queued events`);
    while (this.eventQueue.length > 0) {
      const event = this.eventQueue.shift()!;
      try {
        const eventData = JSON.stringify(event);
        this.dataChannel.send(eventData);
        console.log('📤 Sent queued event:', event.type);
      } catch (error) {
        console.error('❌ Failed to send queued event:', error);
        break;
      }
    }
  }

  // Send text message to the conversation
  sendTextMessage(text: string): void {
    this.sendEvent({
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: text
          }
        ]
      }
    });

    // Trigger response generation
    this.sendEvent({
      type: 'response.create',
      response: {
        modalities: ['text', 'audio'],
        instructions: 'Rispondi in italiano in modo professionale e preciso.'
      }
    });
  }

  // Send audio data (for manual audio streaming)
  sendAudioData(audioData: ArrayBuffer): void {
    const base64Audio = btoa(String.fromCharCode(...new Uint8Array(audioData)));

    this.sendEvent({
      type: 'input_audio_buffer.append',
      audio: base64Audio
    });
  }

  // Commit audio buffer (end of audio input)
  commitAudioInput(): void {
    this.sendEvent({
      type: 'input_audio_buffer.commit'
    });
  }

  // Enhanced audio recording with real-time streaming
  private setupAudioRecording(): void {
    if (!this.mediaStream) return;

    try {
      this.audioContext = new AudioContext({ sampleRate: 24000 });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create audio processor for real-time audio streaming
      const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        // Check if recording is active before processing audio
        if (!this.sessionStateSubject.value.isRecording) return;

        const inputBuffer = event.inputBuffer.getChannelData(0);
        const outputBuffer = new ArrayBuffer(inputBuffer.length * 2);
        const view = new DataView(outputBuffer);

        // Convert float32 to 16-bit PCM
        for (let i = 0; i < inputBuffer.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputBuffer[i]));
          view.setInt16(i * 2, sample * 0x7FFF, true);
        }

        // Send audio data to OpenAI in real-time
        this.sendAudioData(outputBuffer);
      };

      source.connect(processor);
      processor.connect(this.audioContext.destination);

      console.log('🎤 Real-time audio streaming setup complete');
    } catch (error) {
      console.error('❌ Failed to setup audio recording:', error);
    }
  }

  // Start recording (enable microphone)
  startRecording(): void {
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach(track => {
        track.enabled = true;
      });
      this.updateSessionState({ isRecording: true });
    }
  }

  // Stop recording (disable microphone)
  stopRecording(): void {
    if (this.mediaStream) {
      this.mediaStream.getAudioTracks().forEach(track => {
        track.enabled = false;
      });
      this.updateSessionState({ isRecording: false });
    }
  }

  // Cancel current response
  cancelResponse(): void {
    this.sendEvent({
      type: 'response.cancel'
    });
  }

  // Update session configuration
  updateSessionConfig(config: Partial<SessionConfig>): void {
    this.sessionConfig = { ...this.sessionConfig, ...config };

    if (this.isConnected()) {
      this.sendEvent({
        type: 'session.update',
        session: this.sessionConfig
      });
    }
  }

  // Check connection status
  isConnected(): boolean {
    return this.sessionStateSubject.value.isConnected;
  }

  // Disconnect from OpenAI
  async disconnect(): Promise<void> {
    try {
      console.log('🔌 Disconnecting from OpenAI WebRTC...');

      // Stop media stream
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }

      // Clear event queue
      this.eventQueue = [];

      // Close data channel
      if (this.dataChannel) {
        this.dataChannel.close();
        this.dataChannel = null;
      }

      // Close peer connection
      if (this.peerConnection) {
        this.peerConnection.close();
        this.peerConnection = null;
      }

      // Close audio context
      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }

      this.updateSessionState({
        isConnected: false,
        isConnecting: false,
        isRecording: false,
        isSpeaking: false,
        sessionId: undefined,
        error: undefined
      });

      console.log('✅ Disconnected from OpenAI WebRTC');
    } catch (error) {
      console.error('❌ Error during disconnect:', error);
    }
  }

  private updateSessionState(updates: Partial<WebRTCSessionState>): void {
    const currentState = this.sessionStateSubject.value;
    const newState = { ...currentState, ...updates };
    this.sessionStateSubject.next(newState);
  }

  // Get current session state
  getCurrentState(): WebRTCSessionState {
    return this.sessionStateSubject.value;
  }

  // Get available audio devices
  async getAudioDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('❌ Failed to get audio devices:', error);
      return [];
    }
  }

  // Switch audio input device
  async switchAudioDevice(deviceId: string): Promise<void> {
    try {
      // Stop current stream
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
      }

      // Get new stream with specified device
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: deviceId },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
          channelCount: 1
        }
      });

      // Replace track in peer connection
      if (this.peerConnection && this.mediaStream) {
        const audioTrack = this.mediaStream.getAudioTracks()[0];
        const sender = this.peerConnection.getSenders().find(s =>
          s.track && s.track.kind === 'audio'
        );

        if (sender) {
          await sender.replaceTrack(audioTrack);
        }
      }

      console.log('🎤 Switched to audio device:', deviceId);
    } catch (error) {
      console.error('❌ Failed to switch audio device:', error);
      this.errorSubject.next('Failed to switch audio device');
    }
  }
}