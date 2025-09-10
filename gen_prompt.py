# prompt_router.py
# Seleziona automaticamente il prompt più adatto alla casistica del documento.
# Usage rapido:
#   from prompt_router import choose_prompt
#   name, prompt, debug = choose_prompt(file_name, analysis_text)
#   print(name); print(prompt[:800])

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable

# ---------------------------------------------------------------------------
# Utility: normalizzazione testo e tokenizzazione semplice
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _findall(pattern: str, text: str) -> int:
    try:
        return len(re.findall(pattern, text, flags=re.IGNORECASE))
    except re.error:
        return 0


def _contains_any(text: str, keywords: list[str]) -> int:
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
Sei un analista aziendale. Analizza esclusivamente il documento "{file_name}" incluso di seguito, senza usare fonti esterne né inferenze oltre il testo.

=== DOCUMENTO (testo estratto) ===
{analysis_text}
=== FINE DOCUMENTO ===

OBIETTIVO
1) Restituisci un JSON strutturato.
2) Subito dopo il JSON, una sintesi esecutiva in italiano.

REGOLE
- Cita SEMPRE le pagine per numeri/date/percentuali: usa "p. X".
- Se un’informazione non è presente, usa null/"" e spiega in "note".
- Mantieni toni professionali; max 5 punti per sezione.
- Output SOLO nei due blocchi indicati.

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
Scrivi 120–200 parole, tono da analista, richiamando "p. X" dopo i numeri chiave.
</SINTESI>
"""


def PROMPT_BILANCIO(file_name: str, analysis_text: str) -> str:
    return f"""
Sei un equity/credit analyst. Analizza il documento "{file_name}" qui sotto, senza usare fonti esterne.
Riporta valori solo se presenti e indica sempre la pagina di provenienza.

=== DOCUMENTO ===
{analysis_text}
=== FINE DOCUMENTO ===

PRODUCI due sezioni nell’ordine:
1) <KPI_JSON> … </KPI_JSON>
2) <SINTESI> … </SINTESI>

<KPI_JSON>
{{
  "periodi_coperti": [],
  "conto_economico": {{
    "ricavi": [{{"periodo":"", "valore":"","unita":"", "fonte_pagina":""}}],
    "ebitda": [],
    "ebit": [],
    "utile_netto": []
  }},
  "stato_patrimoniale": {{
    "cassa_e_equivalenti": [],
    "debito_finanziario_totale": [],
    "patrimonio_netto": []
  }},
  "cash_flow": {{
    "cfo": [],
    "cfi": [],
    "cff": [],
    "capex": []
  }},
  "margini_e_ratios": [
    {{"nome":"margine EBITDA","periodo":"","valore":"","unita":"%","fonte_pagina":""}},
    {{"nome":"PFN","periodo":"","valore":"","unita":"","fonte_pagina":""}},
    {{"nome":"PFN/EBITDA","periodo":"","valore":"","unita":"x","fonte_pagina":""}}
  ],
  "guidance_o_outlook": [{{"testo":"","periodo":"","fonte_pagina":""}}],
  "eventi_straordinari": [{{"descrizione":"","impatto":"","fonte_pagina":""}}],
  "rischi": [{{"descrizione":"","impatto":"","probabilita":"","fonte_pagina":""}}],
  "note": ""
}}
</KPI_JSON>

<SINTESI>
In 150–250 parole, evidenzia crescita/contrazione, driver, rischi, outlook, covenant e deadline. Usa “p. X” accanto ai numeri specifici.
</SINTESI>

REGOLE
- Compila solo ciò che è presente. Lascialo vuoto se manca.
- Non calcolare ratios se non sono nel testo, a meno che tutte le grandezze per un calcolo semplice siano presenti (in tal caso mostra il calcolo nella SINTESI con p. X).
"""


def PROMPT_FATTURATO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come sales/revenue analyst. Analizza il documento "{file_name}" qui sotto (no fonti esterne).

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
120–180 parole con trend, scostamenti, mix, rischi/opportunità. Cita “p. X” dopo i numeri.
</SINTESI>
"""


def PROMPT_MAGAZZINO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come operations/inventory analyst. Analizza il documento "{file_name}" (solo contenuto incluso).

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
120–180 parole focalizzate su rotazione, OTIF, obsoleti, rischi operativi e prossimi passi, con citazioni “p. X”.
</SINTESI>
"""


def PROMPT_CONTRATTO(file_name: str, analysis_text: str) -> str:
    return f"""
Agisci come legal/ops analyst. Analizza il contratto "{file_name}" basandoti solo sul testo.

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
            "conto economico",
            "stato patrimoniale",
            "cash flow",
            "rendiconto finanziario",
            "ebitda",
            "ebit",
            "utile netto",
            "ricavi",
            "capex",
            "pfn",
            "margine",
            "indebitamento",
            "covenant",
        ],
        patterns=[
            r"\b€\s?\d",
            r"\bmln\b|\bmlrd\b|\bmld\b",
            r"\b%|\bpp\b|\bbp(?:s)?\b",
            r"\bifrs\b",
            r"\bfy20\d{2}\b|\b1h\d{2}\b|\bq[1-4]\b",
        ],
        min_score_to_win=1.5,
    ),
    "fatturato": CaseRule(
        name="fatturato",
        builder=PROMPT_FATTURATO,
        keywords=[
            "fatturato",
            "vendite",
            "ricavi netti",
            "ordini",
            "backlog",
            "listino",
            "sconti",
            "promozioni",
            "mix prodotto",
            "volumi",
            "asp",
            "quota di mercato",
            "pipeline",
            "forecast",
            "yoy",
            "mom",
        ],
        patterns=[r"\b€\s?\d", r"\b%\b", r"\byoy\b", r"\bqoq\b|\bmom\b"],
        min_score_to_win=1.2,
    ),
    "magazzino": CaseRule(
        name="magazzino",
        builder=PROMPT_MAGAZZINO,
        keywords=[
            "magazzino",
            "inventario",
            "giacenze",
            "rotazione",
            "obsoleti",
            "rotti di stock",
            "scorte",
            "lead time",
            "otif",
            "wms",
            "lotti",
            "livello di servizio",
            "resi",
            "sku",
        ],
        patterns=[r"\bOTIF\b", r"\bSKU\b", r"\bgiorni\b.*\bgiacenza\b"],
        min_score_to_win=1.2,
    ),
    "contratto": CaseRule(
        name="contratto",
        builder=PROMPT_CONTRATTO,
        keywords=[
            "contratto",
            "accordo",
            "clausola",
            "penali",
            "sla",
            "durata",
            "rinnovo",
            "corrispettivo",
            "risoluzione",
            "recesso",
            "foro",
            "legge applicabile",
            "responsabilità",
            "riservatezza",
            "proprietà intellettuale",
            "allegati",
        ],
        patterns=[r"\bart\.\s?\d+", r"\bcapo\s+[ivx]+\b", r"\bsezione\b\s*\d+"],
        min_score_to_win=1.2,
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
    if any(k in fname for k in rule.keywords):
        score *= rule.boost_if_filename

    # segnali generici: valute/percentuali/datetime → piccolo boost alla finanza/vendite
    if rule.name in {"bilancio", "fatturato"}:
        generic_signals = _findall(r"[€$£]\s?\d", analysis_text) + _findall(
            r"\d[\.,]\d+%|\bpercentuale\b", analysis_text
        )
        score += 0.2 * generic_signals

    return score


# ---------------------------------------------------------------------------
# Entry point: scelta del prompt
# ---------------------------------------------------------------------------


def choose_prompt(file_name: str, analysis_text: str) -> tuple[str, str, dict]:
    """
    Ritorna (prompt_name, prompt_text, debug_info)
    - prompt_name: 'bilancio' | 'fatturato' | 'magazzino' | 'contratto' | 'generale'
    - prompt_text: string pronto da inviare al modello
    - debug_info: dizionario con punteggi e motivazioni
    """
    scores = {}
    for name, rule in ROUTER.items():
        scores[name] = _score_case(rule, file_name, analysis_text)

    # migliore candidato oltre la soglia minima; altrimenti GENERAL
    best_name = max(scores, key=scores.get)
    best_rule = ROUTER[best_name]
    if scores[best_name] >= best_rule.min_score_to_win:
        chosen_name = best_name
        builder = best_rule.builder
    else:
        chosen_name = "generale"
        builder = PROMPT_GENERAL

    prompt_text = builder(file_name, analysis_text)
    debug = {
        "scores": scores,
        "chosen": chosen_name,
        "file_hint": file_name,
        "length_chars": len(analysis_text),
    }
    return chosen_name, prompt_text, debug


# ---------------------------------------------------------------------------
# Facile estensione: aggiungi nuove casistiche
# ---------------------------------------------------------------------------
# Esempio per "presentazione/slide" o "marketing":
#
# def PROMPT_PRESENTAZIONE(file_name, analysis_text): ...
# ROUTER["presentazione"] = CaseRule(
#     name="presentazione",
#     builder=PROMPT_PRESENTAZIONE,
#     keywords=["presentazione", "slide", "agenda", "appendice", "roadmap"],
#     patterns=[r"^\s*slide\s+\d+", r"\bagenda\b"],
#     min_score_to_win=1.1
# )
#
# Done!
