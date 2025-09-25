# 🎙️ Voice Input Setup - OpenAI Realtime API

## Configurazione Iniziale

### 1. Configurazione API Key
Per abilitare la funzionalità voice, aggiungi la tua API key OpenAI nel file environment:

```typescript
// src/environments/environment.ts
export const environment = {
  // ... altre configurazioni
  openaiApiKey: 'sk-your-openai-api-key-here'
};
```

### 2. Requisiti del Browser
- **Chrome/Edge**: ✅ Supporto completo WebRTC
- **Firefox**: ✅ Supporto completo WebRTC
- **Safari**: ⚠️ Supporto parziale WebRTC
- **Mobile**: ✅ Supportato su iOS Safari e Android Chrome

### 3. Permessi Richiesti
L'applicazione richiederà automaticamente:
- **Microfono**: Per registrazione audio
- **Connessione Internet**: Per comunicazione WebSocket con OpenAI

## Funzionalità Implementate

### Voice Input Component
- **Pulsante floating**: Posizionato accanto al campo query
- **Stati visivi**:
  - 🎤 Grigio: Inattivo
  - 🟢 Verde: Sessione attiva, pronto all'ascolto
  - 🔴 Rosso: Registrazione in corso (con animazione pulse)
- **Feedback visivo**: Indicatori di stato in tempo reale

### Flusso Operativo
1. **Click sul pulsante voice**: Avvia sessione OpenAI Realtime
2. **Autorizzazione microfono**: Il browser richiede permessi
3. **Connessione WebSocket**: Collegamento a OpenAI Realtime API
4. **Click per registrare**: Inizia registrazione audio
5. **Trascrizione automatica**: Il testo appare nel campo query
6. **Esecuzione query**: Manuale o automatica (configurabile)

### Gestione Errori
- **API Key mancante**: Messaggio di errore con istruzioni
- **Permessi negati**: Guida per abilitare microfono
- **Connessione fallita**: Retry automatico e fallback
- **Audio non supportato**: Graceful degradation

## Architettura Tecnica

### Services
- **`VoiceChatService`**: Gestione OpenAI Realtime API
  - WebSocket connection
  - MediaRecorder per audio
  - AudioContext per playback
  - State management (BehaviorSubject)

### Components
- **`VoiceInputComponent`**: UI per input vocale
  - Standalone component riutilizzabile
  - Event emitters per integrazione
  - Responsive design

### Integration
- **`DocumentRagComponent`**: Integrazione nel Query RAG
  - Voice button posizionato accanto al textarea
  - Auto-populate della query con transcript
  - Notifiche di stato

## Configurazioni Avanzate

### OpenAI Realtime Settings
```typescript
// Configurazione sessione (in VoiceChatService)
const sessionConfig = {
  type: 'session.update',
  session: {
    modalities: ['text', 'audio'],
    instructions: 'Sei un assistente AI per sistema RAG...',
    voice: 'alloy', // alloy, echo, fable, onyx, nova, shimmer
    input_audio_format: 'pcm16',
    output_audio_format: 'pcm16',
    input_audio_transcription: {
      model: 'whisper-1'
    }
  }
};
```

### Media Recorder Options
```typescript
this.mediaRecorder = new MediaRecorder(audioStream, {
  mimeType: 'audio/webm;codecs=opus'
});
```

### Audio Context Settings
```typescript
this.audioStream = await navigator.mediaDevices.getUserMedia({
  audio: {
    echoCancellation: true,
    noiseSuppression: true,
    sampleRate: 24000
  }
});
```

## Troubleshooting

### Errori Comuni

**1. "OpenAI API key non configurata"**
```bash
Soluzione: Aggiungi la chiave API in environment.ts
```

**2. "Accesso al microfono negato"**
```bash
Soluzione:
- Chrome: Settings > Privacy > Microphone > Allow
- Firefox: Address bar > Shield icon > Allow microphone
```

**3. "WebSocket connection failed"**
```bash
Possibili cause:
- API key non valida
- Rate limit OpenAI superato
- Connessione internet instabile
```

**4. "Audio playback issues"**
```bash
Soluzione: Verifica supporto AudioContext del browser
```

### Debug Mode
Per abilitare logging esteso:
```typescript
// In VoiceChatService constructor
console.log('Voice service initialized');
localStorage.setItem('voice-debug', 'true');
```

## Costi OpenAI

### Realtime API Pricing (Dec 2024)
- **Input audio**: ~$0.06 per minuto
- **Output audio**: ~$0.24 per minuto
- **Input text**: $0.005 per 1K tokens
- **Output text**: $0.02 per 1K tokens

### Ottimizzazioni
- Sessioni brevi per ridurre costi
- Timeout automatico dopo inattività
- Compressione audio ottimizzata
- Caching delle trascrizioni comuni

## Best Practices

### UX Guidelines
1. **Feedback immediato**: Animazioni e stati visivi chiari
2. **Gestione errori**: Messaggi user-friendly
3. **Accessibility**: Supporto screen reader
4. **Performance**: Lazy loading components

### Security
1. **API Key protection**: Mai committare in repo
2. **Environment variables**: Usa .env per production
3. **Rate limiting**: Implementa throttling lato client
4. **Audio privacy**: Inform users about data processing

### Monitoring
```typescript
// Analytics tracking
trackVoiceUsage(duration: number, success: boolean) {
  // Implement analytics
}
```

## Estensioni Future

### Roadmap
- [ ] **Multi-language support**: Italiano, Inglese, Francese
- [ ] **Voice commands**: "Cerca", "Cancella", "Esporta"
- [ ] **Audio responses**: Playback delle risposte
- [ ] **Offline mode**: Speech Recognition API fallback
- [ ] **Voice training**: Personalizzazione per utente
- [ ] **Integration with RAG**: Voice-to-RAG direct pipeline

### Advanced Features
- **Voice biometrics**: User identification
- **Sentiment analysis**: Emotion detection
- **Meeting transcription**: Multi-speaker support
- **Voice synthesis**: Custom voice models