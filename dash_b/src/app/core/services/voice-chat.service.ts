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

      // Ensure voices are loaded
      if (this.speechSynthesis.getVoices().length === 0) {
        this.speechSynthesis.addEventListener('voiceschanged', () => {
          console.log('🔊 Speech synthesis voices loaded:', this.speechSynthesis?.getVoices().length);
        });
      }

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

      // Preprocess text for more natural speech
      const processedText = this.preprocessTextForSpeech(text);
      console.log('🎙️ Original text length:', text.length, '→ Processed:', processedText.length);

      // Create utterance
      const utterance = new SpeechSynthesisUtterance(processedText);

      // Select the best Italian voice available
      const bestVoice = this.getBestItalianVoice();
      if (bestVoice) {
        utterance.voice = bestVoice;
        console.log('🎙️ Using voice:', bestVoice.name, '- Quality:', bestVoice.localService ? 'High (Local)' : 'Standard (Remote)');
      }

      utterance.lang = 'it-IT'; // Italian voice

      // Advanced voice parameters for more natural speech
      utterance.rate = 0.78; // Even slower for better naturalness
      utterance.pitch = 0.9; // Lower pitch for warmth
      utterance.volume = 0.95; // Clear volume

      // Add slight pauses for breathing (helps with naturalness)
      if (processedText.length > 200) {
        utterance.rate = 0.75; // Slower for longer texts
      }

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

      // For very long texts, consider chunking for better naturalness
      if (processedText.length > 800) {
        console.log('📝 Long text detected, using chunked speech for better quality');
        this.speakTextInChunks(processedText);
        return;
      }

      // Start speaking
      this.speechSynthesis.speak(utterance);

      console.log('🔊 Speaking text:', processedText.substring(0, 50) + '...');

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

  // Get the best Italian voice available
  private getBestItalianVoice(): SpeechSynthesisVoice | null {
    if (!this.speechSynthesis) return null;

    const voices = this.speechSynthesis.getVoices();
    console.log('🎙️ Available voices:', voices.length);

    // Priority order for Italian voices (best to worst)
    const preferredVoiceNames = [
      // High-quality Italian voices
      'Alice', 'Federica', 'Paola', 'Valentina', // macOS Italian voices
      'Microsoft Elsa - Italian', 'Microsoft Cosimo - Italian', // Windows Italian voices
      'Google italiano', 'it-IT-Standard-A', 'it-IT-Standard-B', // Google Italian voices
      'Italian Female', 'Italian Male', // Generic Italian voices
    ];

    // First try: Find preferred high-quality voices
    for (const preferredName of preferredVoiceNames) {
      const voice = voices.find(v =>
        v.name.includes(preferredName) &&
        (v.lang === 'it-IT' || v.lang === 'it')
      );
      if (voice) {
        console.log('🎯 Found preferred voice:', voice.name, '- Local:', voice.localService);
        return voice;
      }
    }

    // Second try: Any Italian voice with local service (higher quality)
    const localItalianVoice = voices.find(v =>
      (v.lang === 'it-IT' || v.lang === 'it') && v.localService
    );
    if (localItalianVoice) {
      console.log('🎯 Found local Italian voice:', localItalianVoice.name);
      return localItalianVoice;
    }

    // Third try: Any Italian voice
    const italianVoice = voices.find(v =>
      v.lang === 'it-IT' || v.lang === 'it'
    );
    if (italianVoice) {
      console.log('🎯 Found Italian voice:', italianVoice.name);
      return italianVoice;
    }

    // Fallback: Any voice that sounds good (prefer female voices for warmth)
    const fallbackVoice = voices.find(v =>
      v.name.toLowerCase().includes('female') ||
      v.name.toLowerCase().includes('woman') ||
      v.name.toLowerCase().includes('alice') ||
      v.name.toLowerCase().includes('samantha')
    );

    if (fallbackVoice) {
      console.log('🎯 Using fallback voice:', fallbackVoice.name);
      return fallbackVoice;
    }

    console.log('⚠️ No suitable voice found, using default');
    return null;
  }

  // Get list of available Italian voices for user selection
  getAvailableItalianVoices(): SpeechSynthesisVoice[] {
    if (!this.speechSynthesis) return [];

    const voices = this.speechSynthesis.getVoices();
    return voices.filter(v =>
      v.lang === 'it-IT' || v.lang === 'it' ||
      v.name.toLowerCase().includes('italian')
    );
  }

  // Preprocess text to make speech more natural
  private preprocessTextForSpeech(text: string): string {
    let processedText = text;

    // Remove excessive markdown formatting that sounds bad when spoken
    processedText = processedText.replace(/\*\*(.*?)\*\*/g, '$1'); // Remove bold
    processedText = processedText.replace(/\*(.*?)\*/g, '$1'); // Remove italic
    processedText = processedText.replace(/`(.*?)`/g, '$1'); // Remove code formatting

    // Add natural pauses for better speech flow
    processedText = processedText.replace(/\. /g, '. ... '); // Pause after sentences
    processedText = processedText.replace(/: /g, ': ... '); // Pause after colons
    processedText = processedText.replace(/; /g, '; ... '); // Pause after semicolons

    // Improve pronunciation of numbers and percentages
    processedText = processedText.replace(/(\d+)%/g, '$1 per cento'); // Replace % with "per cento"
    processedText = processedText.replace(/(\d+),(\d+)/g, '$1 virgola $2'); // Italian decimal format
    processedText = processedText.replace(/€\s*(\d+)/g, '$1 euro'); // Currency formatting

    // Replace common abbreviations with full words for better pronunciation
    processedText = processedText.replace(/\bEBITDA\b/g, 'E-BIT-DA');
    processedText = processedText.replace(/\bEBIT\b/g, 'E-BIT');
    processedText = processedText.replace(/\bEBT\b/g, 'E-B-T');
    processedText = processedText.replace(/\bROI\b/g, 'R-O-I');
    processedText = processedText.replace(/\bROE\b/g, 'R-O-E');
    processedText = processedText.replace(/\bPFN\b/g, 'P-F-N');

    // Improve readability of long numbers
    processedText = processedText.replace(/(\d{1,3})\.(\d{3})/g, '$1 mila $2'); // Thousands
    processedText = processedText.replace(/(\d+)\.000/g, '$1 mila'); // Exact thousands

    // Add breathing pauses for long paragraphs
    const sentences = processedText.split('. ');
    if (sentences.length > 3) {
      // Add longer pause every 2-3 sentences
      for (let i = 2; i < sentences.length; i += 3) {
        sentences[i] = sentences[i] + ' ..... '; // Longer pause
      }
      processedText = sentences.join('. ');
    }

    // Clean up multiple spaces and dots
    processedText = processedText.replace(/\s+/g, ' '); // Multiple spaces to single
    processedText = processedText.replace(/\.{5,}/g, '.....'); // Normalize long pauses

    return processedText.trim();
  }

  // Speak long text in chunks for better naturalness
  private async speakTextInChunks(text: string): Promise<void> {
    if (!this.speechSynthesis) return;

    // Split text into natural chunks (by sentences or paragraphs)
    const chunks = this.splitTextIntoChunks(text);
    console.log('📝 Speaking in', chunks.length, 'chunks for better quality');

    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];

      // Create utterance for this chunk
      const utterance = new SpeechSynthesisUtterance(chunk);

      // Apply voice settings
      const bestVoice = this.getBestItalianVoice();
      if (bestVoice) {
        utterance.voice = bestVoice;
      }

      utterance.lang = 'it-IT';
      utterance.rate = 0.8; // Slightly faster for chunks
      utterance.pitch = 0.9;
      utterance.volume = 0.95;

      // Add pause between chunks
      if (i > 0) {
        await this.delay(300); // 300ms pause between chunks
      }

      // Speak this chunk
      await new Promise<void>((resolve) => {
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        this.speechSynthesis!.speak(utterance);
      });
    }
  }

  // Split text into natural speaking chunks
  private splitTextIntoChunks(text: string): string[] {
    const maxChunkLength = 400;
    const chunks: string[] = [];

    // First try to split by paragraphs (double newlines or numbered lists)
    let paragraphs = text.split(/\n\n|\d+\.\s/);

    for (let paragraph of paragraphs) {
      paragraph = paragraph.trim();
      if (!paragraph) continue;

      if (paragraph.length <= maxChunkLength) {
        chunks.push(paragraph);
      } else {
        // Split long paragraphs by sentences
        const sentences = paragraph.split(/\.\s+/);
        let currentChunk = '';

        for (const sentence of sentences) {
          if (currentChunk.length + sentence.length + 2 <= maxChunkLength) {
            currentChunk += (currentChunk ? '. ' : '') + sentence;
          } else {
            if (currentChunk) {
              chunks.push(currentChunk + '.');
            }
            currentChunk = sentence;
          }
        }

        if (currentChunk) {
          chunks.push(currentChunk + (currentChunk.endsWith('.') ? '' : '.'));
        }
      }
    }

    return chunks.filter(chunk => chunk.length > 0);
  }

  // Helper method for delays
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}