# prompt_router.py
# Seleziona automaticamente il prompt più adatto alla casistica del documento.
# Adattato per integrazione con il sistema RAG

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility: normalizzazione testo e tokenizzazione semplice
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    """Normalizza il testo per il confronto"""
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _findall(pattern: str, text: str) -> int:
    """Conta le occorrenze di un pattern nel testo"""
    try:
        return len(re.findall(pattern, text, flags=re.IGNORECASE))
    except re.error:
        return 0


def _contains_any(text: str, keywords: list[str]) -> int:
    """Conta le occorrenze di keyword nel testo"""
    score = 0
    for kw in keywords:
        # parole intere o bigrammi; tolleranza accenti
        kw_re = re.escape(kw).replace(r"\ ", r"\s+")
        score += _findall(rf"\b{kw_re}\b", text)
    return score


# ---------------------------------------------------------------------------
# Prompt templates (inseriscono {file_name} e {analysis_text}).
# N.B.: JSON con doppie graffe {{ }} per non interferire con str.format()
# ---------------------------------------------------------------------------


def PROMPT_GENERAL(file_name: str, analysis_text: str) -> str:
    return f"""
Sei un analista aziendale esperto. Analizza esclusivamente il documento "{file_name}" incluso di seguito, senza usare fonti esterne né inferenze oltre il testo.

=== DOCUMENTO (testo estratto) ===
{analysis_text}
=== FINE DOCUMENTO ===

OBIETTIVO
1) Restituisci un JSON strutturato con i dati chiave del documento
2) Subito dopo il JSON, fornisci una sintesi esecutiva in italiano

REGOLE
- Cita SEMPRE le pagine per numeri/date/percentuali: usa "p. X"
- Se un'informazione non è presente, usa null/"" e spiega in "note"
- Mantieni toni professionali e analitici
- Output SOLO nei due blocchi indicati

<JSON>
{{
  "tipo_documento": "",
  "oggetto_principale": "",
  "elementi_chiave": [
    {{"punto": "", "fonte_pagina": ""}}
  ],
  "dati_quantitativi": [
    {{"descrizione": "", "valore": "", "unita": "", "periodo_riferimento": "", "fonte_pagina": ""}}
  ],
  "date_rilevanti": [
    {{"evento": "", "data_iso": "", "fonte_pagina": ""}}
  ],
  "stakeholder_menzionati": [
    {{"nome": "", "ruolo": "", "fonte_pagina": ""}}
  ],
  "rischi_o_issue": [
    {{"descrizione": "", "impatto": "", "probabilita": "", "fonte_pagina": ""}}
  ],
  "conclusioni_o_raccomandazioni": [
    {{"testo": "", "fonte_pagina": ""}}
  ],
  "lacune_e_incertezze": [
    {{"tema": "", "motivo_mancanza": "", "fonte_pagina": ""}}
  ],
  "note": ""
}}
</JSON>

<SINTESI>
Scrivi 120–200 parole con tono da analista professionale, richiamando "p. X" dopo i numeri chiave.
</SINTESI>
"""


def PROMPT_BILANCIO(file_name: str, analysis_text: str) -> str:
    # Per il momento non gestito
    client_adapter_json = None

    logger.info(f"Generating PROMPT_BILANCIO for file '{file_name}'")

    from string import Template

    PROMPT_TMPL = Template(r"""
    Sei un equity/credit analyst esperto in documenti finanziari italiani. Analizza il documento "$FILE_NAME" e, se fornito, usa anche l'adapter opzionale in fondo.

    COMPETENZE SPECIALIZZATE
    - Numeri italiani: 1.234,56 -> 1234.56; (123) o -123 -> numero negativo
    - Percentuali: 5,2% -> 5.2%
    - Scale: "valori in migliaia/milioni" => moltiplica x1.000 / x1.000.000
    - Sinonimi (parziali): fatturato=ricavi=vendite; PFN=posizione finanziaria netta; MOL=EBITDA; risultato operativo=EBIT; utile=utile netto=risultato netto; costi del personale=costo del lavoro; Opex=spese operative; costi materie/merci=consumi/COGS
    - Validazioni: Attivo=Passivo; PFN=Debito lordo-Cassa; Margine lordo=Ricavi-COGS

    === DOCUMENTO ===
    $ANALYSIS_TEXT
    === FINE DOCUMENTO ===

    === ADAPTER_OPZIONALE ===
    $CLIENT_ADAPTER_JSON
    === FINE ADAPTER ===

    ISTRUZIONI OPERATIVE (schema-agnostiche)
    1) Riconoscimento sezioni: individua blocchi "Ricavi/Revenue/Fatturato", "Costi/COGS/Opex", "Stato patrimoniale/Attivo/Passivo/Posizione finanziaria", "Cash flow", "Indicatori (EBITDA/EBIT/Margini)", "Guidance/Rischi/Eventi". Se l'ADAPTER è presente, usa le sue mappature come prioritarie; altrimenti usa sinonimi/regex/contesto tabellare.
    2) Parsing numeri & scale: rispetta il formato italiano e applica la scala dichiarata nella stessa tabella/sezione (es. "valori in migliaia"). Se più scale compaiono, applica quella più vicina alla tabella/valore.
    3) Provenienza: per ogni numero estratto indica sempre "p. X" o "tab. Y" (se non reperibile, lascia vuoto).
    4) Periodi: normalizza etichette a {"Consuntivo/Actual", "Budget", "AnnoPrecedente/Prev. Year"}. Se più periodi sono presenti (trimestre, YTD, FY), mantieni quello esplicitamente richiesto dal documento o il più vicino al titolo; in dubbio, privilegia YTD/Consuntivo.
    5) Coerenza: verifica Attivo=Passivo; PFN=Debito lordo-Cassa; Gross margin=Ricavi-COGS. Se mismatch, segnala in "note" e NON correggere i numeri.
    6) Confronti: calcola Δ e Δ% solo quando entrambe le grandezze sono presenti nel documento. Per sottoricavi, riporta anche incidenza % sul totale ricavi del periodo.
    7) Rigidità dati: NON inventare. Campi non reperiti restano vuoti. Indica la scala applicata in "note".
    8) Output: produci ESATTAMENTE due sezioni nell'ordine:
    a) <KPI_JSON> … </KPI_JSON>
    b) <SINTESI> … </SINTESI>

    <KPI_JSON>
    {
    "periodi_coperti": [],
    "conto_economico": {
        "ricavi": [{"periodo":"","valore":"","unita":"EUR","fonte_pagina":""}],
        "ebitda": [],
        "ebit": [],
        "utile_netto": []
    },
    "dettaglio_ricavi": [
        {"nome":"vendite","periodo":"","valore":"","unita":"EUR","incidenza_pct":"","fonte_pagina":"","confidence":""},
        {"nome":"servizi","periodo":"","valore":"","unita":"EUR","incidenza_pct":"","fonte_pagina":"","confidence":""},
        {"nome":"assistenze","periodo":"","valore":"","unita":"EUR","incidenza_pct":"","fonte_pagina":"","confidence":""},
        {"nome":"altri_ricavi","periodo":"","valore":"","unita":"EUR","incidenza_pct":"","fonte_pagina":"","confidence":""},
        {"nome":"recupero_spese_trasporto","periodo":"","valore":"","unita":"EUR","incidenza_pct":"","fonte_pagina":"","confidence":""}
    ],
    "costi": {
        "consumi_cogs": [],
        "costo_del_lavoro": [],
        "opex": [
        {"nome":"industriali","periodo":"","valore":"","unita":"EUR","fonte_pagina":"","confidence":""},
        {"nome":"commerciali","periodo":"","valore":"","unita":"EUR","fonte_pagina":"","confidence":""},
        {"nome":"amministrative","periodo":"","valore":"","unita":"EUR","fonte_pagina":"","confidence":""},
        {"nome":"totali_opex","periodo":"","valore":"","unita":"EUR","fonte_pagina":"","confidence":""}
        ],
        "accantonamenti_e_svalutazioni": [],
        "ammortamenti": [],
        "oneri_finanziari": []
    },
    "stato_patrimoniale": {
        "cassa_e_equivalenti": [],
        "debito_finanziario_totale": [],
        "patrimonio_netto": [],
        "pfn": []
    },
    "cash_flow": { "cfo": [], "cfi": [], "cff": [], "capex": [] },
    "margini_e_ratios": [
        {"nome":"gross_margin","periodo":"","valore":"","unita":"EUR","fonte_pagina":"","confidence":""},
        {"nome":"gross_margin_pct","periodo":"","valore":"","unita":"%","fonte_pagina":"","confidence":""},
        {"nome":"margine EBITDA","periodo":"","valore":"","unita":"%","fonte_pagina":"","confidence":""},
        {"nome":"PFN/EBITDA","periodo":"","valore":"","unita":"x","fonte_pagina":"","confidence":""}
    ],
    "guidance_o_outlook": [{"testo":"","periodo":"","fonte_pagina":""}],
    "eventi_straordinari": [{"descrizione":"","impatto":"","fonte_pagina":""}],
    "rischi": [{"descrizione":"","impatto":"","probabilita":"","fonte_pagina":""}],
    "raw_fields": [{"label_originale":"","valore":"","periodo":"","unita":"","fonte_pagina":""}],
    "note": ""
    }
    </KPI_JSON>

    <SINTESI>
    (150–250 parole; blocchi: Ricavi, Costi, Indicatori, Stato Patrimoniale/Consolidato se presenti. Per ogni numero specifico: "p. X/tab. Y". Evidenzia driver, Δ vs AnnoPrecedente e vs Budget quando disponibili, rischi e outlook. Non dedurre oltre i dati disponibili.)
    </SINTESI>

    REGOLE FINALI
    - Compila solo ciò che è presente nel documento/adapter. In caso di ambiguità, riporta il campo in "raw_fields" e non forzare la mappatura.
    - Non calcolare ratios se mancano le grandezze necessarie. Indica sempre la scala applicata in "note".
    """)

    prompt = PROMPT_TMPL.substitute(
        FILE_NAME=file_name, ANALYSIS_TEXT=analysis_text, CLIENT_ADAPTER_JSON=client_adapter_json or ""
    )

    return prompt


def PROMPT_FATTURATO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come sales/revenue analyst esperto. Analizza il documento "{file_name}" qui sotto (no fonti esterne).

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

OUTPUT:
<JSON>
{{
  "periodi_coperti": [],
  "fatturato_totale": [{{"periodo":"","valore":"","valuta":"","var_yoy":"","fonte_pagina":""}}],
  "ripartizione": {{
    "per_prodotto": [{{"prodotto":"","periodo":"","valore":"","valuta":"","fonte_pagina":""}}],
    "per_cliente": [{{"cliente":"","periodo":"","valore":"","valuta":"","fonte_pagina":""}}],
    "per_area": [{{"area":"","periodo":"","valore":"","valuta":"","fonte_pagina":""}}]
  }},
  "kpi_vendite": [
    {{"nome":"ASP","periodo":"","valore":"","unita":"","fonte_pagina":""}},
    {{"nome":"volumi","periodo":"","valore":"","unita":"","fonte_pagina":""}},
    {{"nome":"order backlog","periodo":"","valore":"","unita":"","fonte_pagina":""}}
  ],
  "scostamenti_e_driver": [{{"driver":"","impatto":"","fonte_pagina":""}}],
  "prezzi_sconti_promozioni": [{{"descrizione":"","impatto_pct":"","fonte_pagina":""}}],
  "pipeline_e_forecast": [{{"periodo":"","valore_forecast":"","assunzioni":"","fonte_pagina":""}}],
  "rischi_opportunita": [{{"descrizione":"","probabilita":"","impatto":"","fonte_pagina":""}}],
  "note": ""
}}
</JSON>

<SINTESI>
120–180 parole con trend di vendita, scostamenti, mix prodotto/cliente, rischi/opportunità. Cita "p. X" dopo i numeri.
</SINTESI>
"""


def PROMPT_MAGAZZINO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come operations/inventory analyst esperto. Analizza il documento "{file_name}" (solo contenuto incluso).

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

OUTPUT:
<JSON>
{{
  "periodi_coperti": [],
  "giacenze_totali": [{{"periodo":"","valore":"","unita":"","giorni_giacenza":"","fonte_pagina":""}}],
  "rotture_di_stock": [{{"sku":"","periodo":"","n_eventi":"","fonte_pagina":""}}],
  "eccessi_e_obsoleti": [{{"sku_o_categoria":"","valore":"","valuta":"","percentuale_su_scorte":"","fonte_pagina":""}}],
  "rotazione_magazzino": [{{"periodo":"","indice_rotazione":"","unita":"x","fonte_pagina":""}}],
  "lead_time_e_servizio": [{{"fornitore_o_linea":"","lt_medio_giorni":"","livello_servizio_pct":"","fonte_pagina":""}}],
  "kpi_logistici": [
    {{"nome":"OTIF","periodo":"","valore_pct":"","fonte_pagina":""}},
    {{"nome":"tasso resi","periodo":"","valore_pct":"","fonte_pagina":""}}
  ],
  "azioni_correttive": [{{"tema":"","azione":"","responsabile":"","scadenza":"","fonte_pagina":""}}],
  "note": ""
}}
</JSON>

<SINTESI>
120–180 parole focalizzate su rotazione, OTIF, obsoleti, rischi operativi e prossimi passi, con citazioni "p. X".
</SINTESI>
"""


def PROMPT_CONTRATTO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come legal/ops analyst esperto. Analizza il contratto "{file_name}" basandoti solo sul testo.

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

OUTPUT:
<JSON>
{{
  "parti_coinvolte": [{{"nome":"","ruolo":"","fonte_pagina":""}}],
  "oggetto_e_ambito": {{"testo":"","fonte_pagina":""}},
  "durata_e_decorrenza": {{"inizio":"","fine":"","rinnovo":"","fonte_pagina":""}},
  "corrispettivi_e_pagamenti": [{{"descrizione":"","importo":"","valuta":"","scadenza":"","fonte_pagina":""}}],
  "kpi_sla_penali": [{{"kpi":"","soglia":"","misura":"","penale":"","fonte_pagina":""}}],
  "obblighi_delle_parti": [{{"parte":"","obbligo":"","fonte_pagina":""}}],
  "limitazioni_di_responsabilita": [{{"clausola":"","massimale":"","esclusioni":"","fonte_pagina":""}}],
  "proprieta_intellettuale_e_riservatezza": [{{"tema":"","clausola":"","fonte_pagina":""}}],
  "recesso_risoluzione": [{{"caso":"","preavviso":"","conseguenze":"","fonte_pagina":""}}],
  "legge_applicabile_forum": {{"legge":"","foro":"","fonte_pagina":""}},
  "allegati_richiamati": [{{"titolo":"","fonte_pagina":""}}],
  "rischi_operativi": [{{"descrizione":"","mitigazione":"","fonte_pagina":""}}],
  "note": ""
}}
</JSON>

<SINTESI>
Executive summary (120–180 parole) con clausole critiche e red flag. Cita pagine (p. X).
</SINTESI>

REGOLE: non inferire; se mancano dettagli, lascia campi vuoti e segnala in "note".
"""


def PROMPT_PRESENTAZIONE(file_name: str, analysis_text: str) -> str:
    """Prompt specializzato per presentazioni e slide"""
    return f"""
Sei un business analyst esperto. Analizza la presentazione "{file_name}" basandoti solo sul contenuto fornito.

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

[Analisi tipo: PRESENTAZIONE]

OUTPUT:
<JSON>
{{
  "titolo_presentazione": "",
  "autore_o_azienda": "",
  "data_presentazione": "",
  "obiettivo_principale": "",
  "struttura_presentazione": [
    {{"sezione": "", "argomento": "", "slide_range": "", "fonte_pagina": ""}}
  ],
  "messaggi_chiave": [
    {{"messaggio": "", "supporto_dati": "", "fonte_pagina": ""}}
  ],
  "dati_e_metriche": [
    {{"metrica": "", "valore": "", "periodo": "", "trend": "", "fonte_pagina": ""}}
  ],
  "conclusioni": [
    {{"punto": "", "fonte_pagina": ""}}
  ],
  "next_steps": [
    {{"azione": "", "responsabile": "", "timeline": "", "fonte_pagina": ""}}
  ],
  "allegati_o_backup": [{{"descrizione": "", "fonte_pagina": ""}}],
  "note": ""
}}
</JSON>

<SINTESI>
Riassunto esecutivo (150-200 parole) che cattura l'essenza della presentazione, i messaggi chiave e le raccomandazioni principali. Cita "slide X" o "p. X" per riferimenti specifici.
</SINTESI>
"""


def PROMPT_SCADENZARIO(file_name: str, analysis_text: str) -> str:
    # Check if the content is already a structured JSON
    import json

    try:
        # Try to parse as JSON
        json_data = json.loads(analysis_text)
        # If it's valid JSON with expected scadenzario keys, use special prompt
        if isinstance(json_data, dict) and any(
            key in json_data for key in ["periodi_coperti", "aging_bucket", "kpi", "totali"]
        ):
            from services.prompt_scadenzario_json import PROMPT_SCADENZARIO_JSON

            logger.info(f"Using specialized JSON prompt for scadenzario file {file_name}")
            return PROMPT_SCADENZARIO_JSON(file_name, analysis_text)
    except (json.JSONDecodeError, ImportError):
        # Not JSON or import failed, continue with normal prompt
        pass

    return f"""
Sei un credit/AR analyst. Analizza lo scadenzario "{file_name}" qui sotto, senza usare fonti esterne.
Riporta valori solo se presenti e indica sempre la pagina di provenienza.

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

PRODUCI due sezioni nell'ordine:
1) <KPI_JSON> … </KPI_JSON>
2) <SINTESI> … </SINTESI>

<KPI_JSON>
{{
  "periodi_coperti": [],
  "perimetro": "",
  "valute": [],
  "totali": {{
    "crediti_lordi": [{{"periodo":"","valore":"","unita":"EUR","fonte_pagina":""}}],
    "fondo_svalutazione": [],
    "crediti_netto": [],
    "numero_clienti_attivi": []
  }},
  "aging_bucket": [
    {{"bucket":"0-30 gg","periodo":"","valore":"","unita":"EUR","percentuale_su_totale":"","unita_percent":"%","fonte_pagina":""}},
    {{"bucket":"31-60 gg","periodo":"","valore":"","unita":"EUR","percentuale_su_totale":"","unita_percent":"%","fonte_pagina":""}},
    {{"bucket":"61-90 gg","periodo":"","valore":"","unita":"EUR","percentuale_su_totale":"","unita_percent":"%","fonte_pagina":""}},
    {{"bucket":">90 gg","periodo":"","valore":"","unita":"EUR","percentuale_su_totale":"","unita_percent":"%","fonte_pagina":""}}
  ],
  "past_due": {{
    "totale_scaduto": [{{"periodo":"","valore":"","unita":"EUR","fonte_pagina":""}}],
    "dpd_medio_ponderato": [],
    "percentuale_scaduto_su_totale": []
  }},
  "incassi_e_flussi": {{
    "incassi_periodo": [],
    "credit_notes_periodo": [],
    "sconti_pronti_pagamento": []
  }},
  "termini_e_pratiche": {{
    "termini_pagamento_standard": [],
    "termini_pagamento_median": [],
    "dilazioni_concesse": []
  }},
  "kpi": {{
    "dso": [
      {{"periodo":"","valore":"","unita":"giorni","metodo":"","fonte_pagina":""}}
    ],
    "turnover_crediti": [],
    "dpd_>90gg_percent": []
  }},
  "concentrazione_rischio": {{
    "top1_percent_su_totale": [],
    "top5_percent_su_totale": [],
    "top10_percent_su_totale": [],
    "primi_clienti": [
      {{"cliente":"","periodo":"","valore":"","unita":"EUR","percentuale_su_totale":"","unita_percent":"%","fonte_pagina":""}}
    ],
    "related_party_exposure": []
  }},
  "qualita_crediti": {{
    "posizioni_in_contenzioso": [],
    "piani_rientro_e_promesse_pagamento": [],
    "garanzie_collaterali": [],
    "write_off": [],
    "coverage_fondo_su_scaduto": []
  }},
  "disaggregazioni": {{
    "per_geografia": [],
    "per_business_unit_o_prodotto": [],
    "per_valuta": []
  }},
  "note": ""
}}
</KPI_JSON>

<SINTESI>
In 150–250 parole, evidenzia: andamento di DSO e scaduto (p. X), bucket critici (p. X), concentrazione clienti (p. X), qualità del credito (accantonamenti, write-off, contenziosi; p. X), termini di pagamento e dilazioni (p. X), incassi recenti e trend (p. X), rischi principali e azioni di mitigazione (p. X).
Se il documento riporta le grandezze necessarie, puoi calcolare DSO con metodo esplicitato:
- DSO = (Crediti commerciali medi / Vendite giornaliere) * 365 (p. X, p. Y).
- Oppure, se il doc specifica un metodo diverso, usa quello e indicane la formula e le pagine.
Mostra ogni calcolo con numeri e "p. X". Evita inferenze se i dati non sono presenti.
</SINTESI>

REGOLE
- Compila solo ciò che è presente. Lascialo vuoto se manca.
- Indica sempre la pagina di provenienza (campo "fonte_pagina").
- Non calcolare KPI/ratios se non sono nel testo, a meno che tutte le grandezze per un calcolo semplice siano presenti (in tal caso mostra il calcolo nella SINTESI con p. X e specifica il metodo).
- Mantieni le unità coerenti (EUR, %, giorni). Non stimare tassi di cambio.
- Se il documento mescola AR e AP, limita l'analisi ai crediti (AR) o specifica chiaramente il perimetro.
"""


def PROMPT_REPORT_DETTAGLIATO(file_name: str, analysis_text: str) -> str:
    """Prompt per analisi approfondita stile NotebookLM di report finanziari complessi"""
    return f"""
Sei un senior equity research analyst specializzato in documenti finanziari italiani. Produci un'analisi professionale approfondita del documento "{file_name}" seguendo gli standard di un investment memorandum.

COMPETENZE AVANZATE RICHIESTE:
- **Parsing numeri italiani**: 1.234.567,89 (format italiano), (123) = negativo, 5,2%
- **Gestione scale**: "valori in migliaia/milioni" → conversione automatica
- **Sinonimi finanziari**: fatturato=ricavi=vendite; EBITDA=MOL; PFN=debito netto
- **Validazioni contabili**: Attivo=Passivo, PFN=Debito-Cassa, Margine=Ricavi-COGS
- **Provenienza granulare**: "p.12|tab.1|riga:Ricavi" per ogni numero
- **Confronti strutturati**: YoY%, vs Budget%, scostamenti quantificati

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

METODOLOGIA OPERATIVA:
1. **Estrazione accurata**: Riconosci tutti i numeri in formato italiano
2. **Conversioni**: Applica scale dichiarate ("in migliaia" × 1.000)
3. **Normalizzazione**: Uniforma sinonimi (fatturato → ricavi)
4. **Validazione**: Controlla coerenze contabili basilari
5. **Bridge analysis**: Spiega variazioni con numeri precisi
6. **Citations**: Ogni dato con fonte esatta (p.X, tab.Y)

GENERA UN REPORT COMPLETO IN FORMATO PROFESSIONALE:

<INVESTMENT_MEMO>
# Investment Memorandum: Analisi Finanziaria Approfondita

**Data Analisi**: [Data corrente]
**Documento Fonte**: {file_name}
**Tipo Analisi**: Performance Review & Strategic Assessment

## EXECUTIVE SUMMARY
[Paragrafo di 200-250 parole con numeri italiani correttamente interpretati]

## 1. ANALISI RICAVI E CRESCITA
### 1.1 Performance Complessiva
- **Ricavi Totali**: [Valore con formato italiano, es. 5.214.095 €]
- **Crescita YoY**: [% con decimale virgola, es. 7,4%]
- **Vs Budget**: [Scostamento quantificato con segno]

### 1.2 Analisi per Business Line
[Per ogni categoria di ricavi con parsing preciso numeri italiani]

## 2. STRUTTURA COSTI E MARGINALITÀ
### 2.1 Gross Margin Analysis
- **Margine Lordo**: XX,X% (vs XX,X% P.Y.) [format italiano]
- **Driver breakdown** con variazioni quantificate

### 2.2 OPEX Analysis
- **OPEX Totali**: € XXX.XXX (+/-XX,X% YoY)
- **Per categoria** con numeri in formato italiano

## 3. PROFITABILITY METRICS
### 3.1 EBITDA Performance
- **EBITDA**: € XXX.XXX (XX,X% margin)
- **Bridge Analysis**: Volume € +XXX, Prezzo € +XXX, Costi € -XXX

### 3.2 Coerenze Contabili Verificate
[Controlli automatici: Attivo=Passivo, PFN=Debito-Cassa, etc.]

## 4. CONCLUSIONI E RACCOMANDAZIONI
### Key Takeaways:
1. **Performance**: [Con numeri italiani accurati]
2. **Risks**: [Quantificati in € e %]
3. **Actions**: [Con target numerici specifici]
</INVESTMENT_MEMO>

<JSON_METRICS>
{{
  "numeri_italiani_processati": [
    {{"raw": "1.234,56", "parsed": 1234.56, "confidence": 0.95}},
    {{"raw": "(123)", "parsed": -123, "confidence": 1.0}}
  ],
  "scale_rilevata": "migliaia|milioni|unità",
  "valuta_prevalente": "EUR|USD",
  "coerenze_verificate": [
    {{"test": "attivo_passivo", "passed": true, "dettaglio": ""}}
  ],
  "performance_summary": {{
    "ricavi_totali": 0,
    "crescita_yoy_pct": 0,
    "ebitda_margin_pct": 0,
    "validation_errors": []
  }}
}}
</JSON_METRICS>
"""


def PROMPT_CDC(file_name: str, analysis_text: str) -> str:
    """Prompt per analisi Centri di Costo (CDC)"""
    return f"""
Sei un analista di Controllo di Gestione specializzato in Centri di Costo (CDC). Analizza esclusivamente il documento "{file_name}" incluso di seguito, senza usare fonti esterne né inferenze oltre il testo.

=== DOCUMENTO (testo estratto) ===
{analysis_text}
=== FINE DOCUMENTO ===

OBIETTIVO
1) Restituisci un JSON strutturato con i dati chiave di analisi CDC (perimetro, totali, dettagli per CDC, scostamenti, driver, allocazioni, rischi).
2) Subito dopo il JSON, fornisci una sintesi esecutiva in italiano.

REGOLE
- Cita SEMPRE le pagine per numeri/date/percentuali: usa "p. X".
- Se un'informazione non è presente, usa null/"" e spiega in "note".
- Mantieni toni professionali, analitici e neutri.
- Non aggiungere conoscenze esterne o stime: usa solo il testo fornito.
- Standard numerici: usa valori numerici grezzi (es. 12345.67), separa l'unità in "unita" (es. "EUR", "%", "FTE").
- Date in formato ISO (DD.MM.YYYY). Periodi come intervalli "DD.MM.YYYY/DD.MM.YYYY".
- Se il documento riporta più CDC, riporta sia il quadro totale sia il dettaglio per singolo CDC.
- Esegui verifiche di coerenza (es. somma delle righe = totale; budget/consuntivo/forecast coerenti con periodi); segnala esiti in "riconciliazioni_e_controlli".
- Output SOLO nei due blocchi indicati (<JSON> e <SINTESI>), senza testo aggiuntivo.

<JSON>
{{
  "tipo_documento": "",
  "oggetto_principale": "",
  "perimetro": {{
    "azienda": "",
    "business_unit": "",
    "periodo_da": "",
    "periodo_a": "",
    "valuta": "",
    "fonte_pagina": ""
  }},
  "quadro_sintetico": [
    {{
      "indicatore": "Totale costi CDC",
      "budget": "",
      "consuntivo": "",
      "forecast": "",
      "scostamento_budget_consuntivo": "",
      "scostamento_budget_consuntivo_perc": "",
      "scostamento_consuntivo_forecast": "",
      "scostamento_consuntivo_forecast_perc": "",
      "periodo_riferimento": "",
      "fonte_pagina": ""
    }}
  ],
  "cdc": [
    {{
      "nome_cdc": "",
      "codice_cdc": "",
      "responsabile": "",
      "fonte_pagina": "",
      "classificazione_costi": [
        {{"categoria": "Personale/Servizi/IT/Logistica/Altri/Intercompany",
          "budget": "", "consuntivo": "", "forecast": "",
          "scostamento_budget_consuntivo": "", "scostamento_budget_consuntivo_perc": "",
          "fonte_pagina": ""}}
      ],
      "kpi": [
        {{"nome": "Costo/FTE", "valore": "", "unita": "EUR/FTE", "periodo_riferimento": "", "fonte_pagina": ""}},
        {{"nome": "Run-rate mensile", "valore": "", "unita": "EUR/mese", "periodo_riferimento": "", "fonte_pagina": ""}}
      ],
      "fte": [
        {{"tipologia": "Interni/Esterni", "valore": "", "periodo_riferimento": "", "fonte_pagina": ""}}
      ],
      "volumi_attivita": [
        {{"metrica": "ordini/ticket/ore/macchinari", "valore": "", "periodo_riferimento": "", "fonte_pagina": ""}}
      ],
      "driver_allocazione": [
        {{"driver": "m2/FTE/ore macchina/ricavi", "base": "", "coefficiente": "", "fonte_pagina": ""}}
      ],
      "natura_costi": [
        {{"tipo": "Fissi/Variabili/Direct/Indirect", "importo_consuntivo": "", "fonte_pagina": ""}}
      ],
      "note_cdc": ""
    }}
  ],
  "ribaltamenti_e_allocazioni": [
    {{"da_cdc": "", "a_cdc": "", "criterio": "", "base": "", "importo": "", "periodo_riferimento": "", "fonte_pagina": ""}}
  ],
  "scomposizione_scostamenti": [
    {{"cdc": "", "tipo": "Prezzo/Volume/Mix/Efficienza", "importo": "", "percentuale": "", "periodo_riferimento": "", "fonte_pagina": ""}}
  ],
  "impegni_contrattuali_e_PO_aperti": [
    {{"fornitore": "", "descrizione": "", "impegno_residuo": "", "scadenza_iso": "", "fonte_pagina": ""}}
  ],
  "capex_e_ammortamenti": [
    {{"progetto": "", "stato": "", "capex": "", "avvio_iso": "", "ammortamento_periodo": "", "fonte_pagina": ""}}
  ],
  "accantonamenti_ratei_risconti": [
    {{"descrizione": "", "importo": "", "competenza_periodo": "", "fonte_pagina": ""}}
  ],
  "riconciliazioni_e_controlli": [
    {{"test": "Somma CDC = totale riportato", "esito": "OK/KO", "scostamento": "", "fonte_pagina": ""}},
    {{"test": "Coerenza periodo (budget/consuntivo/forecast)", "esito": "OK/KO", "dettaglio": "", "fonte_pagina": ""}}
  ],
  "dati_quantitativi": [
    {{"descrizione": "Costo medio FTE", "valore": "", "unita": "EUR/FTE", "periodo_riferimento": "", "fonte_pagina": ""}},
    {{"descrizione": "Tasso di assorbimento overhead", "valore": "", "unita": "%", "periodo_riferimento": "", "fonte_pagina": ""}}
  ],
  "date_rilevanti": [
    {{"evento": "Approvazione budget CDC", "data_iso": "", "fonte_pagina": ""}}
  ],
  "stakeholder_menzionati": [
    {{"nome": "", "ruolo": "Responsabile CDC/Controller/Approvatore", "fonte_pagina": ""}}
  ],
  "rischi_o_issue": [
    {{"descrizione": "Sforamento budget/criteri di ribaltamento non aggiornati/accantonamenti insufficienti",
      "impatto": "Basso/Medio/Alto", "probabilita": "Bassa/Media/Alta", "fonte_pagina": ""}}
  ],
  "conclusioni_o_raccomandazioni": [
    {{"testo": "", "fonte_pagina": ""}}
  ],
  "lacune_e_incertezze": [
    {{"tema": "Dati mancanti/criteri non specificati", "motivo_mancanza": "Non presente nel documento/ambiguità",
      "fonte_pagina": ""}}
  ],
  "note": ""
}}
</JSON>

<SINTESI>
Scrivi 120–200 parole con tono da analista di Controllo di Gestione. Evidenzia quadro sintetico (budget, consuntivo, forecast), principali scostamenti e driver, eventuali ribaltamenti, rischi e raccomandazioni, richiamando le fonti con "p. X" dopo i numeri chiave.
</SINTESI>
"""


# ---------------------------------------------------------------------------
# Router configuration: parole-chiave e pesi
# ---------------------------------------------------------------------------


@dataclass
class CaseRule:
    name: str
    builder: Callable[[str, str], str]
    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)  # regex avanzate
    weight_keywords: float = 1.0
    weight_patterns: float = 2.0
    boost_if_filename: float = 1.5  # moltiplicatore se il nome file contiene keyword
    min_score_to_win: float = 1.0  # soglia minima per preferirlo al general


ROUTER: dict[str, CaseRule] = {
    "bilancio": CaseRule(
        name="bilancio",
        builder=PROMPT_BILANCIO,
        keywords=[
            "bilancio",
            "relazione finanziaria",
            "financial statement",
            "annual report",
            "conto economico",
            "stato patrimoniale",
            "cash flow",
            "rendiconto finanziario",
            "ebitda",
            "ebit",
            "utile netto",
            "ricavi",
            "revenues",
            "capex",
            "pfn",
            "margine",
            "indebitamento",
            "covenant",
            "trimestrale",
            "semestrale",
            "annuale",
        ],
        patterns=[
            r"\b€\s?\d",
            r"\bmln\b|\bmlrd\b|\bmld\b|\bmillion\b|\bbillion\b",
            r"\b%|\bpp\b|\bbp(?:s)?\b",
            r"\bifrs\b|\bgaap\b",
            r"\bfy20\d{2}\b|\b1h\d{2}\b|\bq[1-4]\b",
            r"\b20\d{2}\s+vs\s+20\d{2}\b",
        ],
        min_score_to_win=1.5,
    ),
    "fatturato": CaseRule(
        name="fatturato",
        builder=PROMPT_FATTURATO,
        keywords=[
            "fatturato",
            "vendite",
            "sales",
            "revenue",
            "ricavi netti",
            "ordini",
            "orders",
            "backlog",
            "listino",
            "pricing",
            "sconti",
            "discount",
            "promozioni",
            "mix prodotto",
            "product mix",
            "volumi",
            "volumes",
            "asp",
            "average selling price",
            "quota di mercato",
            "market share",
            "pipeline",
            "forecast",
            "previsioni vendite",
            "yoy",
            "mom",
            "cliente",
            "customer",
            "breakdown",
            "trimestre",
            "quarter",
        ],
        patterns=[
            r"\b€\s?\d",
            r"\b%\b",
            r"\byoy\b|\byear.over.year\b",
            r"\bqoq\b|\bmom\b|\bq[1-4]\b",
            r"\bgrowth\s+rate\b",
            r"\bbreakdown\b",
        ],
        min_score_to_win=1.2,
        boost_if_filename=2.0,  # Maggior peso al nome file per vendite
    ),
    "magazzino": CaseRule(
        name="magazzino",
        builder=PROMPT_MAGAZZINO,
        keywords=[
            "magazzino",
            "inventario",
            "inventory",
            "stock",
            "giacenze",
            "rotazione",
            "turnover",
            "obsoleti",
            "obsolete",
            "rotture di stock",
            "stock out",
            "scorte",
            "lead time",
            "otif",
            "on time in full",
            "wms",
            "warehouse",
            "lotti",
            "batch",
            "livello di servizio",
            "service level",
            "resi",
            "returns",
            "sku",
            "logistica",
            "logistics",
            "supply chain",
        ],
        patterns=[
            r"\bOTIF\b",
            r"\bSKU\b",
            r"\bgiorni\b.*\bgiacenza\b",
            r"\bDIO\b|\bDSO\b|\bDPO\b",
            r"\bwarehouse\b",
        ],
        min_score_to_win=1.2,
    ),
    "contratto": CaseRule(
        name="contratto",
        builder=PROMPT_CONTRATTO,
        keywords=[
            "contratto",
            "contract",
            "accordo",
            "agreement",
            "clausola",
            "clause",
            "penali",
            "penalties",
            "sla",
            "service level agreement",
            "durata",
            "duration",
            "rinnovo",
            "renewal",
            "corrispettivo",
            "consideration",
            "risoluzione",
            "termination",
            "recesso",
            "withdrawal",
            "foro",
            "jurisdiction",
            "legge applicabile",
            "governing law",
            "responsabilità",
            "liability",
            "riservatezza",
            "confidentiality",
            "proprietà intellettuale",
            "intellectual property",
            "allegati",
            "exhibits",
            "garanzie",
            "warranties",
        ],
        patterns=[
            r"\bart\.\s?\d+",
            r"\bcapo\s+[ivx]+\b",
            r"\bsezione\b\s*\d+",
            r"\bclause\s+\d+",
            r"\bparagraph\s+\d+",
            r"\bwhereas\b",
        ],
        min_score_to_win=1.2,
    ),
    "presentazione": CaseRule(
        name="presentazione",
        builder=PROMPT_PRESENTAZIONE,
        keywords=[
            "presentazione",
            "presentation",
            "slide",
            "slides",
            "agenda",
            "overview",
            "executive summary",
            "sommario esecutivo",
            "roadmap",
            "timeline",
            "milestone",
            "strategy",
            "strategia",
            "business plan",
            "pitch",
            "investor deck",
            "company profile",
            "profilo aziendale",
        ],
        patterns=[
            r"^\s*slide\s+\d+",
            r"\bagenda\b",
            r"\bslide\s+\d+\b",
            r"\bpage\s+\d+\s+of\s+\d+\b",
            r"\b\d+\/\d+\b",  # formato pagina 1/20
        ],
        min_score_to_win=1.1,
    ),
    "scadenzario": CaseRule(
        name="scadenzario",
        builder=PROMPT_SCADENZARIO,
        keywords=[
            "scadenzario",
            "crediti",
            "credits",
            "receivables",
            "aging",
            "dso",
            "days sales outstanding",
            "overdue",
            "scaduto",
            "past due",
            "dpd",
            "days past due",
            "clienti",
            "customers",
            "debitori",
            "debtors",
            "incassi",
            "collections",
            "credit notes",
            "note di credito",
            "termini di pagamento",
            "payment terms",
            "dilazioni",
            "deferrals",
            "contenzioso",
            "litigation",
            "write off",
            "svalutazione",
            "bad debt",
            "fondo rischi",
            "provision",
            "turnover crediti",
            "receivables turnover",
            "concentrazione rischio",
            "risk concentration",
            "garanzie",
            "guarantees",
            "collaterals",
            "coverage",
            "copertura",
            "bucket",
            "fasce",
            "analisi per scadenza",
            "maturity analysis",
            "sconti finanziari",
            "cash discount",
            "pronto pagamento",
            "prompt payment",
        ],
        patterns=[
            r"\bDSO\b",
            r"\bDPD\b",
            r"\b0-30\b|\b31-60\b|\b61-90\b|\b>90\b",
            r"\baging\b",
            r"\bscaduto\b|\boverdue\b|\bpast\s+due\b",
            r"\bcrediti\s+commerciali\b|\breceivables\b",
            r"\bfondo\s+svalutazione\b|\bbad\s+debt\b",
            r"\bturnover\s+crediti\b",
            r"\bcontenzioso\b|\blitigation\b",
            r"\bwrite\s*off\b",
            r"\bincassi\b|\bcollections\b",
            r"\bgiorni\s+di\s+scadenza\b",
            r"\btermini\s+di\s+pagamento\b|\bpayment\s+terms\b",
        ],
        min_score_to_win=1.3,
        boost_if_filename=2.0,  # Maggior peso al nome file per scadenzario
    ),
    "cdc": CaseRule(
        name="cdc",
        builder=PROMPT_CDC,
        keywords=[
            "centri di costo",
            "centro di costo",
            "cdc",
            "cost center",
            "cost centres",
            "controllo di gestione",
            "management control",
            "budgets centri",
            "budget cdc",
            "consuntivo cdc",
            "forecast cdc",
            "scostamenti budget",
            "variance analysis",
            "allocazioni costi",
            "cost allocation",
            "ribaltamenti",
            "ripartizioni",
            "driver allocazione",
            "allocation drivers",
            "responsabile centro",
            "center manager",
            "overhead",
            "costi indiretti",
            "indirect costs",
            "costi diretti",
            "direct costs",
            "fte",
            "full time equivalent",
            "personale equivalente",
            "run rate",
            "costo per fte",
            "cost per fte",
            "costi fissi",
            "fixed costs",
            "costi variabili",
            "variable costs",
            "costi del personale",
            "personnel costs",
            "costi servizi",
            "service costs",
            "costi it",
            "it costs",
            "logistica costs",
            "logistics costs",
            "intercompany",
            "inter-company",
            "capex",
            "capital expenditure",
            "ammortamenti",
            "depreciation",
            "accantonamenti",
            "provisions",
            "ratei",
            "accruals",
            "risconti",
            "deferrals",
        ],
        patterns=[
            r"\bCDC[\s\-_]*\d+",  # CDC001, CDC-001, CDC_001
            r"\bC[\.\s]?C[\.\s]?\d+",  # C.C.001, CC001, C C 001
            r"\bCentro[\s]+\d+",  # Centro 001
            r"\b[A-Z]{2,4}[\-_]\d{3,4}\b",  # IT-001, HR_002
            r"\bbudget\s+vs\s+consuntivo\b",
            r"\bbudget\s+vs\s+actual\b",
            r"\bvariance\s+analysis\b",
            r"\bscostamento\s+\d+",
            r"\balloca(zione|tion)\s+\d+",
            r"\bribalta(mento|ments?)\b",
            r"\bFTE\s*[:=]\s*\d+",
            r"\bcosto\s*/\s*FTE\b",
            r"\brun[\s\-]?rate\b",
            r"\boverhead\s+rate\b",
            r"\btasso\s+assorbimento\b",
            r"\bcosti\s+(fissi|variabili|diretti|indiretti)\b",
            r"\b(fixed|variable|direct|indirect)\s+costs?\b",
            r"\bresponsabile\s+centro\b",
            r"\bcenter\s+manager\b",
            r"\bcontroller\s+gestionale\b",
        ],
        min_score_to_win=1.2,
        boost_if_filename=1.8,
    ),
}

# ---------------------------------------------------------------------------
# Scoring: somma ponderata tra keyword, pattern e hint dal nome file
# ---------------------------------------------------------------------------


def _score_case(rule: CaseRule, file_name: str, analysis_text: str) -> float:
    text = _norm(analysis_text)
    fname = _norm(file_name)

    kw_hits = _contains_any(text, rule.keywords)
    pat_hits = sum(_findall(p, analysis_text) for p in rule.patterns)

    score = kw_hits * rule.weight_keywords + pat_hits * rule.weight_patterns

    # boost se il nome file contiene indicatori (es. "Bilancio_2024.pdf")
    if any(k in fname for k in rule.keywords[:5]):  # primi 5 keyword più importanti
        score *= rule.boost_if_filename

    # Special handling for JSON files with structured data
    if rule.name == "scadenzario":
        # Check if it's a JSON with scadenzario-specific keys
        import json

        try:
            json_data = json.loads(analysis_text)
            if isinstance(json_data, dict):
                # Strong indicators for scadenzario
                scadenzario_keys = [
                    "aging_bucket",
                    "past_due",
                    "dso",
                    "dpd",
                    "crediti_lordi",
                    "crediti_netto",
                    "fondo_svalutazione",
                    "totale_scaduto",
                    "dpd_medio_ponderato",
                    "coverage_fondo_su_scaduto",
                    "piani_rientro_e_promesse_pagamento",
                    "qualita_crediti",
                    "concentrazione_rischio",
                    "turnover_crediti",
                ]
                # Count matching keys
                key_matches = sum(1 for key in scadenzario_keys if key in str(json_data))
                if key_matches >= 3:  # If we have 3+ scadenzario keys, it's definitely a scadenzario
                    score += 100  # Strong boost to ensure it wins
                    logger.info(f"Detected JSON scadenzario with {key_matches} matching keys")
        except (json.JSONDecodeError, ValueError):
            # Not JSON, continue with normal scoring
            pass

    # segnali generici: valute/percentuali/datetime → piccolo boost alla finanza/vendite
    if rule.name in {"bilancio", "fatturato"}:
        generic_signals = _findall(r"[€$£]\s?\d", analysis_text) + _findall(
            r"\d[\.,]\d+%|\bpercentuale\b|\bpercent\b", analysis_text
        )
        score += 0.2 * generic_signals

    return score


# ---------------------------------------------------------------------------
# Entry point: scelta del prompt
# ---------------------------------------------------------------------------


def choose_prompt(file_name: str, analysis_text: str) -> tuple[str, str, dict]:
    """
    Ritorna (prompt_name, prompt_text, debug_info)
    - prompt_name: 'bilancio' | 'fatturato' | 'magazzino' | 'contratto' | 'presentazione' | 'generale'
    - prompt_text: string pronto da inviare al modello
    - debug_info: dizionario con punteggi e motivazioni
    """
    scores = {}
    for name, rule in ROUTER.items():
        scores[name] = _score_case(rule, file_name, analysis_text)

    # Sort scores to see the ranking
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # migliore candidato oltre la soglia minima; altrimenti GENERAL
    best_name = max(scores, key=scores.get) if scores else "generale"

    logger.debug(f"Prompt router raw scores for '{file_name}': {best_name}")
    if scores and best_name in ROUTER:
        best_rule = ROUTER[best_name]
        logger.info(
            f"Best candidate '{best_name}' with score {scores[best_name]:.2f}, min_score_to_win: {best_rule.min_score_to_win}"
        )
        if scores[best_name] >= best_rule.min_score_to_win:
            chosen_name = best_name
            builder = best_rule.builder
        else:
            logger.info(
                f"Score {scores[best_name]:.2f} below threshold {best_rule.min_score_to_win}, falling back to generale"
            )
            chosen_name = "generale"
            builder = PROMPT_GENERAL
    else:
        chosen_name = "generale"
        builder = PROMPT_GENERAL

    prompt_text = builder(file_name, analysis_text)

    debug = {
        "scores": scores,
        "chosen": chosen_name,
        "file_hint": file_name,
        "length_chars": len(analysis_text),
        "sorted_scores": sorted_scores,
    }

    logger.info(f"Prompt router: scelto '{chosen_name}' per file '{file_name}'")

    return chosen_name, prompt_text, debug


def get_available_prompts() -> list[str]:
    """Ritorna la lista dei tipi di prompt disponibili"""
    return ["generale"] + list(ROUTER.keys())


def get_prompt_description(prompt_name: str) -> str:
    """Ritorna una descrizione del tipo di prompt"""
    descriptions = {
        "generale": "Analisi generica per qualsiasi tipo di documento",
        "bilancio": "Analisi finanziaria per bilanci e report finanziari",
        "fatturato": "Analisi vendite e ricavi",
        "magazzino": "Analisi logistica e gestione scorte",
        "contratto": "Analisi legale e contrattuale",
        "presentazione": "Analisi di presentazioni e slide deck",
        "scadenzario": "Analisi crediti commerciali e aging receivables",
    }
    return descriptions.get(prompt_name, "Tipo di prompt non riconosciuto")
