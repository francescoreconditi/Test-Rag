# Relazione sui Sistemi di Autenticazione Multi-Tenant

## Executive Summary

Il progetto presenta **DUE sistemi di autenticazione distinti** che operano in parallelo, creando conflitti e problemi di sicurezza. Questa relazione analizza entrambi i sistemi e propone una strategia di consolidamento per mantenere un'architettura multi-tenant robusta e scalabile.

## 1. Analisi dei Sistemi Esistenti

### Sistema 1: FastAPI JWT Authentication (src/presentation/api/auth.py)
**Caratteristiche principali:**
- Basato su JWT con libreria `python-jose`
- Token contiene: `tenant_id`, `user_id`, `email`, `tier`
- Durata sessione: 8 ore (configurabile)
- Integrazione con `TenantContext` per isolamento risorse
- Utilizzato da tutti gli endpoint REST API

**Punti di forza:**
- ✅ Design pulito e modulare
- ✅ Supporto completo multi-tenant
- ✅ Gestione limiti risorse per tenant
- ✅ Facile integrazione con FastAPI Depends

**Punti deboli:**
- ❌ Non persiste sessioni in database
- ❌ Non ha gestione utenti completa
- ❌ Manca audit trail

### Sistema 2: MultiTenantManager (src/core/security/multi_tenant_manager.py)
**Caratteristiche principali:**
- Database SQLite per persistenza
- Token JWT con: `session_id`, `user_email`, `permissions`
- Gestione completa utenti con password hash (PBKDF2)
- Audit trail e security events
- Rate limiting integrato
- Cache in memoria per performance

**Punti di forza:**
- ✅ Persistenza completa in database
- ✅ Gestione utenti con password sicure
- ✅ Audit trail dettagliato
- ✅ Rate limiting per tenant
- ✅ Gestione sessioni con expiry

**Punti deboli:**
- ❌ Token JWT incompatibile con Sistema 1
- ❌ Duplicazione logica con auth.py
- ❌ Non utilizzato consistentemente negli endpoint

## 2. Problemi Identificati

### 2.1 Conflitto Token JWT
I due sistemi generano token JWT con strutture diverse:
```python
# Sistema 1 (auth.py)
{
    "tenant_id": "x",
    "user_id": "admin",
    "email": "admin@company.com",
    "tier": "PREMIUM",
    "exp": 1758233736,
    "iat": 1758204936,
    "iss": "zcs-rag-api"
}

# Sistema 2 (MultiTenantManager)
{
    "session_id": "532c249c-f3b1-439e-bd02",
    "tenant_id": "x",
    "user_id": "admin",
    "user_email": "admin@company.com",
    "permissions": ["read", "write"],
    "exp": 1758233736,
    "iat": 1758204936
}
```

### 2.2 Inconsistenza negli Endpoint
- `/auth/login` ora usa Sistema 1 (dopo la fix)
- Streamlit usa principalmente Sistema 2
- Analytics router ha la sua implementazione
- Mancanza di single source of truth

### 2.3 Duplicazione di Codice
- Creazione tenant duplicata in 3 luoghi
- Gestione sessioni duplicata
- Validazione token duplicata

## 3. Integrazione con Streamlit

L'applicazione Streamlit utilizza un approccio ibrido:
1. **AuthenticationService** per login RLS (Row Level Security)
2. **MultiTenantManager** per gestione tenant
3. **SecureRAGEngine** per isolamento dati
4. Creazione dinamica tenant se non esiste

## 4. Raccomandazioni per Consolidamento

### 4.1 Strategia Proposta: Unificare su MultiTenantManager Enhanced

**Motivazione:** MultiTenantManager ha già tutte le funzionalità enterprise necessarie. Va solo allineato con FastAPI.

### 4.2 Piano di Implementazione

#### Fase 1: Allineamento Token JWT
```python
# Nuovo formato token unificato
{
    "session_id": "uuid",
    "tenant_id": "tenant_x",
    "user_id": "user_123",
    "email": "user@company.com",
    "role": "ADMIN",
    "tier": "PREMIUM",
    "permissions": ["read", "write", "delete"],
    "exp": 1758233736,
    "iat": 1758204936,
    "iss": "zcs-rag-api"
}
```

#### Fase 2: Refactoring auth.py
- Trasformare `auth.py` in un wrapper sottile sopra MultiTenantManager
- Mantenere le funzioni `Depends()` per compatibilità FastAPI
- Delegare tutta la logica a MultiTenantManager

#### Fase 3: Migrazione Database
- Aggiungere colonne mancanti (tier, role) alla tabella tenant_users
- Migrare dati esistenti
- Aggiungere indici per performance

#### Fase 4: Centralizzazione Servizi
```python
# Nuovo servizio unificato
class UnifiedAuthService:
    def __init__(self):
        self.manager = MultiTenantManager()
        self.rls = AuthenticationService()

    async def authenticate(self, email, password, tenant_id=None):
        # Logica unificata qui
        pass

    def verify_token(self, token):
        # Verifica unificata
        pass
```

### 4.3 Configurazione Consigliata

```env
# .env configuration
JWT_SECRET_KEY=<secure-random-key>
JWT_ALGORITHM=HS256
SESSION_DURATION_HOURS=8
ENABLE_MULTI_TENANT=true
ENABLE_RLS=true
ENABLE_AUDIT_TRAIL=true
RATE_LIMIT_PER_MINUTE=100
```

## 5. Benefici della Soluzione Proposta

1. **Single Source of Truth**: Un solo sistema di autenticazione
2. **Persistenza Completa**: Tutte le sessioni in database
3. **Audit Trail**: Tracciabilità completa per compliance
4. **Rate Limiting**: Protezione da abusi
5. **Scalabilità**: Cache + database per performance
6. **Multi-Tenant Nativo**: Isolamento garantito
7. **RLS Integrato**: Row Level Security per dati sensibili

## 6. Priorità di Implementazione

### Alta Priorità (Immediato)
1. ✅ Fix token JWT (COMPLETATO)
2. Allineare formato token tra i sistemi
3. Testare tutti gli endpoint

### Media Priorità (1-2 settimane)
1. Refactoring auth.py
2. Migrazione database
3. Documentazione API

### Bassa Priorità (Futuro)
1. UI amministrazione tenant
2. Metriche e dashboard
3. Integrazione SSO/SAML

## 7. Conclusioni

Il sistema attuale funziona ma presenta rischi di sicurezza e manutenibilità. La soluzione proposta:
- **Mantiene** tutte le funzionalità multi-tenant esistenti
- **Migliora** sicurezza e tracciabilità
- **Semplifica** manutenzione e debugging
- **Prepara** per scale enterprise

**Raccomandazione finale:** Procedere con il consolidamento su MultiTenantManager come base, mantenendo la compatibilità con FastAPI attraverso un layer di astrazione sottile.

## Appendice: Endpoints Analizzati

### Endpoints con Autenticazione Obbligatoria (16)
- `/auth/tenant/info`
- `/analyze/faqs`
- `/analyze/stored`
- `/knowledge/clear`
- Tutti in `/api/analytics/*`

### Endpoints con Autenticazione Opzionale (2)
- `/query`
- `/upload`

### Endpoints Pubblici
- `/auth/login`
- `/health`
- `/docs`
- `/scalar`

---
*Documento generato il: 2025-09-18*
*Autore: Claude Code*
*Versione: 1.0*