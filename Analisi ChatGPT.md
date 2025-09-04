Sì—puoi ottenere risultati **molto** più solidi con un prompt meglio strutturato. NotebookLM sembra “più accurato” perché forza il modello a: citare le fonti (pagine), lavorare a sezioni, estrarre tabelle/valori, dichiarare incertezze e produrre sia un output strutturato sia una sintesi. Possiamo replicare gran parte di questo comportamento con un prompt che:

* impone **vincoli di formato** (JSON + sintesi);
* richiede **riferimenti a pagina** per ogni dato;
* definisce **campi specifici** da estrarre;
* gestisce **assenze/ambiguità**;
* limita **allucinazioni** (“non inferire se non presente”).

Di seguito tre template pronti all’uso (incollabili nel tuo `f"""..."""`), più un paio di varianti “specialistiche”.

---

### 1) Template “Generalista” con output doppio (JSON + Sintesi)

Usalo come sostituto diretto del tuo prompt. Mantiene l’italiano professionale, ma prima produce un JSON verificabile.

```python
prompt = f"""
Sei un analista aziendale. Analizza esclusivamente il contenuto del documento "{{file_name}}"
fornito nel blocco seguente. Non inventare dati non presenti.

=== DOCUMENTO (testo estratto) ===
{{analysis_text}}
=== FINE DOCUMENTO ===

OBIETTIVO
1) Restituisci un JSON strutturato con i campi sotto.
2) Subito dopo il JSON, fornisci una sintesi esecutiva in italiano scorrevole.

REGOLE IMPORTANTI
- Cita SEMPRE le pagine di provenienza per numeri, date, percentuali o citazioni: usa "p. X".
- Se un’informazione non è presente, usa valori null/"" e spiega nel campo "note".
- Non fare deduzioni oltre il testo. Non usare conoscenze esterne.
- Mantieni l’italiano professionale. Nessun elenco troppo lungo: max 5 punti per sezione.
- Formato di output:
  Prima blocco <JSON> ... </JSON>
  Poi blocco <SINTESI> ... </SINTESI>

SCHEMA JSON (usa queste chiavi esatte):
{{
  "tipo_documento": "",
  "oggetto_principale": "",
  "elementi_chiave": [
    {{ "punto": "", "fonte_pagina": "" }}
  ],
  "dati_quantitativi": [
    {{ "descrizione": "", "valore": "", "unita": "", "periodo_riferimento": "", "fonte_pagina": "" }}
  ],
  "date_rilevanti": [
    {{ "evento": "", "data_iso": "", "fonte_pagina": "" }}
  ],
  "stakeholder_menzionati": [
    {{ "nome": "", "ruolo": "", "fonte_pagina": "" }}
  ],
  "rischi_o_issue": [
    {{ "descrizione": "", "impatto": "", "probabilita": "", "fonte_pagina": "" }}
  ],
  "conclusioni_o_raccomandazioni": [
    {{ "testo": "", "fonte_pagina": "" }}
  ],
  "lacune_e_incertezze": [
    {{ "tema": "", "motivo_mancanza": "", "fonte_pagina": "" }}
  ],
  "note": ""
}}

ISTRUZIONI DI ESTRAZIONE
- "tipo_documento": deducilo solo se esplicitato o chiaramente indicato (es. “Bilancio”, “Contratto”, “Presentazione”).
- "oggetto_principale": una frase.
- "elementi_chiave": 3–5 takeaway centrali, ciascuno con pagina.
- "dati_quantitativi": numeri/percentuali/€ con unità e periodo (es. FY2024, 1H25). Indica pagina.
- "date_rilevanti": scadenze, approvazioni, periodi. Usa ISO (YYYY-MM-DD) se possibile.
- "stakeholder_menzionati": persone/enti/ruoli citati.
- "rischi_o_issue": sintetizza rischio, impatto e probabilità se espresse (altrimenti lascia vuoto).
- "conclusioni_o_raccomandazioni": riportale testualmente o parafrasate con pagina.
- "lacune_e_incertezze": cosa non è chiaro o manca.

VALIDAZIONI
- Se non trovi valori quantitativi, lascia "dati_quantitativi": [] e spiega in "note".
- Per ogni numero o citazione, DEVE esserci "fonte_pagina".
- Nessun testo fuori dai due blocchi richiesti.

OUTPUT:
<JSON>
{{JSON qui}}
</JSON>

<SINTESI>
{{Sintesi esecutiva in 120–200 parole, con richiami "p. X" dopo numeri chiave.}}
</SINTESI>
"""
```

**Perché funziona:** obbliga il modello a strutturare l’estrazione, a citare pagine, a non inventare e a separare dati (controllabili) dalla prosa.

---

### 2) Variante “Bilancio/Report finanziario”

Quando il file è un bilancio o una relazione gestionale, chiedi indicatori specifici.

```python
prompt = f"""
Sei un equity/credit analyst. Analizza il documento "{{file_name}}" qui sotto, senza usare fonti esterne.
Riporta valori solo se presenti e indica sempre la pagina di provenienza.

=== DOCUMENTO ===
{{analysis_text}}
=== FINE DOCUMENTO ===

PRODUCI due sezioni nell’ordine:
1) <KPI_JSON> … </KPI_JSON>
2) <SINTESI> … </SINTESI>

SCHEMA KPI_JSON:
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

REGOLE
- Compila solo ciò che è presente. Mantieni array vuoti dove mancano dati.
- Non calcolare ratios se non sono nel testo, a meno che tutte le grandezze siano chiaramente presenti (in tal caso mostra il calcolo sintetico nella SINTESI con p. X).
- Nella SINTESI (150–250 parole) evidenzia: crescita/contrazione, driver, rischi, outlook, covenant, e deadline rilevanti. Usa “p. X” accanto a numeri specifici.
"""
```

---

### 3) Variante “Contratto/Accordo”

Per contratti, spingi su clausole, scadenze, responsabilità.

```python
prompt = f"""
Agisci come legal/ops analyst. Analizza il contratto "{{file_name}}" qui sotto, basandoti solo sul testo.

=== DOCUMENTO ===
{{analysis_text}}
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
Fornisci una executive summary (120–180 parole) con clausole critiche e red flag. Cita pagine (p. X).
</SINTESI>

REGOLE: non inferire; se mancano dettagli lascia campi vuoti e segnala in "note".
"""
```

---

## Accorgimenti pratici (oltre al prompt)

1. **Chunking & paginazione**
   Passa anche l’indice pagina → testo nel tuo `analysis_text` (es. `"[p. 12] …"`). Questo aumenta la precisione delle citazioni.

2. **Parsing tabelle**
   Se stai estraendo dal PDF, conserva separatori e intestazioni di colonna nel testo; aiuta il modello a riconoscere i numeri.

3. **Guardrail anti-allucinazioni**
   Inserisci sempre: “Non usare conoscenze esterne. Non dedurre oltre il testo. Se mancante ⇒ null/array vuoto.”

4. **Doppio output**
   Il blocco `<JSON>` serve a validare/riusare i dati; la `<SINTESI>` è per gli stakeholder.

5. **Policy di riformulazione**
   Se l’input è molto lungo, aggiungi nel prompt: “Se serve, elabora per sezioni (max 3.000 token di input per sezione) e unisci i risultati.”

---

Se vuoi, posso anche darti uno **snippet Python** per pre-taggare ogni riga con la pagina e normalizzare numeri/valute, così il modello ha un contesto più “NotebookLM-like”.



Perfetto — ecco uno **snippet Python** pronto all’uso che:

* estrae il testo da un PDF **pagina per pagina**;
* preserva (per quanto possibile) la struttura delle tabelle;
* **tagga** ogni blocco con il numero di pagina `[p. X]`;
* **normalizza numeri/valute/percentuali** (stile EU → canonico) aggiungendo un’annotazione `⟨norm=...⟩`;
* suddivide il contenuto in **chunk** (utile per modelli con input lunghi).

Copia/incolla in un file, ad es. `pdf_preprocess.py`.

```python
# pdf_preprocess.py
# ------------------------------------------------------------
# Estrazione testo e tabelle da PDF, tagging pagine e normalizzazione numeri
# Dipendenze opzionali: pdfplumber (consigliato). Fallback: PyPDF2.
# ------------------------------------------------------------

from __future__ import annotations
import re
import math
from pathlib import Path

# --- Loader PDF ---------------------------------------------------------------

def _load_with_pdfplumber(pdf_path: str):
    try:
        import pdfplumber
    except ImportError:
        return None
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            # Estrae testo base
            text = page.extract_text() or ""

            # Prova a ricostruire tabelle come pipe-table Markdown (opzionale ma utile)
            tables_md = []
            try:
                tables = page.extract_tables()
                for t in tables or []:
                    if not t or not any(any(cell for cell in row) for row in t):
                        continue
                    # Normalizza celle None → ""
                    t = [[cell if cell is not None else "" for cell in row] for row in t]
                    # Se prima riga sembra header, aggiungi separatore markdown
                    header = t[0]
                    body = t[1:] if len(t) > 1 else []
                    md = ["| " + " | ".join(h.strip() for h in header) + " |"]
                    md.append("| " + " | ".join("---" for _ in header) + " |")
                    for row in body:
                        md.append("| " + " | ".join((str(c).strip()) for c in row) + " |")
                    tables_md.append("\n".join(md))
            except Exception:
                pass

            if tables_md:
                text = (text or "").strip()
                # Inserisce le tabelle in coda, mantenendo la pagina coesa
                text = (text + "\n\n[TABELLE]\n" + "\n\n".join(tables_md)).strip()

            pages.append((i, text))
    return pages

def _load_with_pypdf2(pdf_path: str):
    try:
        import PyPDF2
    except ImportError:
        return None
    pages = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append((i, text))
    return pages

def extract_pdf_pages(pdf_path: str) -> list[tuple[int, str]]:
    """
    Ritorna una lista [(page_num, text), ...].
    Tenta prima pdfplumber (migliore su tabelle), poi PyPDF2.
    """
    pdf_path = str(pdf_path)
    pages = _load_with_pdfplumber(pdf_path)
    if pages is not None:
        return pages
    pages = _load_with_pypdf2(pdf_path)
    if pages is not None:
        return pages
    raise RuntimeError("Installa 'pdfplumber' o 'PyPDF2' (pip install pdfplumber PyPDF2).")

# --- Normalizzazione numeri/valute/percentuali --------------------------------

# Pattern per numeri EU/US con mille separatori (., ' , spazio) e decimali (., ,)
_NUM_RE = re.compile(
    r"""
    (?P<sign>[+-]?)\s*
    (?P<num>
        (?:\d{1,3}(?:[.\s'\u00A0]\d{3})+|\d+)       # parte intera con separatori o semplice
        (?:[.,]\d+)?                                 # decimali opzionali
    )
    \s*
    (?P<suffix>
        %|‰|pp|bp|bps|k|K|m|M|bn|B|mln|mlrd|mld|€|\$|£
    )?
    """,
    re.VERBOSE
)

# Riconosce simbolo valuta anche prima del numero: € 1.234,56
_PRE_CURRENCY_RE = re.compile(r"(?P<cur>[$€£])\s*(?=\d)")

def _canon_number_str(raw: str) -> tuple[str, bool]:
    """
    Converte '1.234,56' o '1,234.56' → '1234.56' (string).
    Ritorna (valore_str, ok) senza unità.
    """
    s = raw.strip()
    # Se entrambe , e . presenti, deduci separatore decimale come l'ultimo dei due
    if "," in s and "." in s:
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        dec_sep = "," if last_comma > last_dot else "."
        thou_sep = "." if dec_sep == "," else ","
        s = s.replace(" ", "").replace("\u00A0", "").replace("'", "")
        s = s.replace(thou_sep, "")
        s = s.replace(dec_sep, ".")
    else:
        # solo virgola → probabile decimale EU
        if "," in s and "." not in s:
            s = s.replace(".", "")              # eventuali mille separator puntini
            s = s.replace(" ", "").replace("\u00A0", "").replace("'", "")
            s = s.replace(",", ".")
        else:
            # solo punto o solo cifre
            s = s.replace(" ", "").replace("\u00A0", "").replace("'", "")
    # Validazione finale
    try:
        float(s)
        return s, True
    except ValueError:
        return raw, False

def _apply_suffix(value: float, suffix: str | None) -> float:
    if not suffix:
        return value
    s = suffix.lower()
    if s in {"k"}:
        return value * 1_000
    if s in {"m", "mln"}:
        return value * 1_000_000
    if s in {"bn"}:
        return value * 1_000_000_000
    if s in {"mlrd", "mld"}:
        return value * 1_000_000_000
    if s in {"pp"}:
        # punti percentuali: lasciamo valore “grezzo”, interpretazione a valle
        return value
    if s in {"bp", "bps"}:
        return value / 10_000.0
    if s in {"%","‰"}:
        # rimane percentuale; la conversione a frazione si fa a valle se serve
        return value
    if s in {"€","$","£"}:
        return value
    return value

def normalize_numbers_in_text(text: str) -> str:
    """
    Aggiunge annotazioni normalizzate dopo i pattern numerici rilevati.
    Esempio:
      "Ricavi € 1.234,5 mln (+12,3%)"
      → "Ricavi € 1.234,5 mln⟨norm=1234500000.0 EUR⟩ (+12,3%)"
    """
    def repl(m: re.Match) -> str:
        sign = m.group("sign") or ""
        num = m.group("num")
        suffix = m.group("suffix")
        raw = (sign + num).strip()
        s_canon, ok = _canon_number_str(raw)
        pre_cur = ""  # valuta davanti
        # Cerca valuta prima del numero immediatamente precedente
        # (usiamo lookbehind “artigianale” ripescando dal contesto)
        start = m.start()
        before = text[max(0, start-2):start]  # corto ma utile: può contenere "€ "
        mpre = _PRE_CURRENCY_RE.search(before)
        if mpre:
            pre_cur = mpre.group("cur")
        # Calcola valore float se possibile (senza toccare %, ‰)
        currency = suffix if suffix in {"€","$","£"} else pre_cur if pre_cur in {"€","$","£"} else None
        if ok:
            value = float(s_canon)
            value_applied = _apply_suffix(value, suffix)
            # Suffix mostrato
            unit_bits = []
            if currency:
                unit_bits.append({"€":"EUR", "$":"USD", "£":"GBP"}[currency])
            if suffix in {"%","‰","pp","bp","bps"}:
                unit_bits.append(suffix)
            unit_str = " ".join(unit_bits)
            annot_val = value_applied
            # Arrotonda in modo leggibile
            if math.isfinite(annot_val):
                if abs(annot_val) >= 1:
                    annot_txt = f"{annot_val:.2f}".rstrip("0").rstrip(".")
                else:
                    annot_txt = f"{annot_val:.6f}".rstrip("0").rstrip(".")
            else:
                annot_txt = str(annot_val)
            if unit_str:
                return f"{m.group(0)}⟨norm={annot_txt} {unit_str}⟩"
            else:
                return f"{m.group(0)}⟨norm={annot_txt}⟩"
        else:
            return m.group(0)
    return _NUM_RE.sub(repl, text)

# --- Tagging pagine e chunking -------------------------------------------------

def tag_pages(pages: list[tuple[int, str]], normalize_numbers: bool = True) -> str:
    """
    Concatena le pagine in un unico testo:
    [p. 1]
    ...
    [p. 2]
    ...
    Se normalize_numbers=True, aggiunge annotazioni ⟨norm=...⟩ ai numeri.
    """
    blocks = []
    for page_num, txt in pages:
        t = txt or ""
        if normalize_numbers:
            t = normalize_numbers_in_text(t)
        blocks.append(f"[p. {page_num}]\n{t}".strip())
    return "\n\n".join(blocks).strip()

def chunk_text(s: str, max_chars: int = 12000, overlap: int = 500) -> list[str]:
    """
    Divide il testo in chunk robusti ai limiti token. Spezza su doppi a capo se possibile.
    """
    if len(s) <= max_chars:
        return [s]
    chunks = []
    i = 0
    while i < len(s):
        end = min(len(s), i + max_chars)
        # prova a retrocedere al precedente separatore
        sep = s.rfind("\n\n", i, end)
        if sep == -1 or sep <= i + 1000:  # evita chunk troppo corti
            sep = end
        chunk = s[i:sep]
        chunks.append(chunk)
        if sep >= len(s):
            break
        i = max(0, sep - overlap)
    # deduplica eventuali sovrapposizioni identiche a fine/inizio
    cleaned = []
    for c in chunks:
        if not cleaned or c != cleaned[-1]:
            cleaned.append(c)
    return cleaned

# --- Pipeline end-to-end -------------------------------------------------------

def build_analysis_text(pdf_path: str,
                        normalize_numbers: bool = True,
                        chunk_size: int | None = None,
                        overlap: int = 500) -> list[str] | str:
    """
    Carica il PDF, tagga pagine, normalizza numeri e (opz.) segmenta.
    - Ritorna lista di chunk se chunk_size è impostato, altrimenti una singola stringa.
    """
    pages = extract_pdf_pages(pdf_path)
    tagged = tag_pages(pages, normalize_numbers=normalize_numbers)
    if chunk_size:
        return chunk_text(tagged, max_chars=chunk_size, overlap=overlap)
    return tagged

# --- Esempio d'uso -------------------------------------------------------------

if __name__ == "__main__":
    # Esempio: python pdf_preprocess.py
    pdf_file = "Bilancio_2024.pdf"
    if not Path(pdf_file).exists():
        print(f"⚠️  File non trovato: {pdf_file}")
    else:
        # 1) Unico blocco per il tuo prompt f"""..."""
        analysis_text = build_analysis_text(pdf_file, normalize_numbers=True)
        print(analysis_text[:2000], "...\n\n[TRONCATO PER DISPLAY]", sep="")

        # 2) Oppure chunk per prompt iterativo
        chunks = build_analysis_text(pdf_file, normalize_numbers=True, chunk_size=12000, overlap=500)
        print(f"\nCreati {len(chunks)} chunk. Primo chunk lunghezza: {len(chunks[0])} caratteri.")
```

### Come integrarlo nel tuo flusso

* Dopo l’estrazione, passa `analysis_text` (o ciascun `chunk`) al prompt “strutturato” che abbiamo definito prima.
* L’annotazione `⟨norm=...⟩` **non sostituisce** il numero originale: serve al modello per capire il valore canonico senza ambiguità (es. milioni, percentuali, valute).
* Se lavori con file molto lunghi, invia i chunk in sequenza e poi chiedi al modello di **fondere i JSON** intermedi in un unico JSON finale (puoi aggiungere una mini-regola nel prompt di merge: “confliggenze → mantieni valore più citato/pagine più recenti”).


Fantastico — ecco un **modulo Python** che sceglie automaticamente il prompt migliore in base al contenuto (e al nome file), con un semplice sistema di **punteggi per parole-chiave** e alcune euristiche (valute, percentuali, termini tipici). Include:

* 4 prompt “specialistici”: **bilancio/finanziario**, **fatturato/vendite**, **magazzino/inventario**, **contratto**
* 1 prompt **generalista** di fallback
* una funzione `choose_prompt(file_name, analysis_text)` che restituisce: `(prompt_name, prompt_text, debug_info)`
* un dizionario di **configurazione** facile da estendere

Salva come `prompt_router.py`.

```python
# prompt_router.py
# Seleziona automaticamente il prompt più adatto alla casistica del documento.
# Usage rapido:
#   from prompt_router import choose_prompt
#   name, prompt, debug = choose_prompt(file_name, analysis_text)
#   print(name); print(prompt[:800])

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

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

def _contains_any(text: str, keywords: List[str]) -> int:
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
    return """
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
""".format(file_name=file_name, analysis_text=analysis_text)

def PROMPT_BILANCIO(file_name: str, analysis_text: str) -> str:
    return """
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
""".format(file_name=file_name, analysis_text=analysis_text)

def PROMPT_FATTURATO(file_name: str, analysis_text: str) -> str:
    return """
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
""".format(file_name=file_name, analysis_text=analysis_text)

def PROMPT_MAGAZZINO(file_name: str, analysis_text: str) -> str:
    return """
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
""".format(file_name=file_name, analysis_text=analysis_text)

def PROMPT_CONTRATTO(file_name: str, analysis_text: str) -> str:
    return """
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
""".format(file_name=file_name, analysis_text=analysis_text)

# ---------------------------------------------------------------------------
# Router configuration: parole-chiave e pesi
# ---------------------------------------------------------------------------

@dataclass
class CaseRule:
    name: str
    builder: Callable[[str, str], str]
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)  # regex avanzate
    weight_keywords: float = 1.0
    weight_patterns: float = 2.0
    boost_if_filename: float = 1.5  # moltiplicatore se il nome file contiene keyword
    min_score_to_win: float = 1.0   # soglia minima per preferirlo al general

ROUTER: Dict[str, CaseRule] = {
    "bilancio": CaseRule(
        name="bilancio",
        builder=PROMPT_BILANCIO,
        keywords=[
            "bilancio", "relazione finanziaria", "conto economico", "stato patrimoniale",
            "cash flow", "rendiconto finanziario", "ebitda", "ebit", "utile netto",
            "ricavi", "capex", "pfn", "margine", "indebitamento", "covenant"
        ],
        patterns=[
            r"\b€\s?\d", r"\bmln\b|\bmlrd\b|\bmld\b", r"\b%|\bpp\b|\bbp(?:s)?\b",
            r"\bifrs\b", r"\bfy20\d{2}\b|\b1h\d{2}\b|\bq[1-4]\b"
        ],
        min_score_to_win=1.5
    ),
    "fatturato": CaseRule(
        name="fatturato",
        builder=PROMPT_FATTURATO,
        keywords=[
            "fatturato", "vendite", "ricavi netti", "ordini", "backlog", "listino",
            "sconti", "promozioni", "mix prodotto", "volumi", "asp", "quota di mercato",
            "pipeline", "forecast", "yoy", "mom"
        ],
        patterns=[r"\b€\s?\d", r"\b%\b", r"\byoy\b", r"\bqoq\b|\bmom\b"],
        min_score_to_win=1.2
    ),
    "magazzino": CaseRule(
        name="magazzino",
        builder=PROMPT_MAGAZZINO,
        keywords=[
            "magazzino", "inventario", "giacenze", "rotazione", "obsoleti",
            "rotti di stock", "scorte", "lead time", "otif", "wms", "lotti",
            "livello di servizio", "resi", "sku"
        ],
        patterns=[r"\bOTIF\b", r"\bSKU\b", r"\bgiorni\b.*\bgiacenza\b"],
        min_score_to_win=1.2
    ),
    "contratto": CaseRule(
        name="contratto",
        builder=PROMPT_CONTRATTO,
        keywords=[
            "contratto", "accordo", "clausola", "penali", "sla", "durata", "rinnovo",
            "corrispettivo", "risoluzione", "recesso", "foro", "legge applicabile",
            "responsabilità", "riservatezza", "proprietà intellettuale", "allegati"
        ],
        patterns=[r"\bart\.\s?\d+", r"\bcapo\s+[ivx]+\b", r"\bsezione\b\s*\d+"],
        min_score_to_win=1.2
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
        generic_signals = (
            _findall(r"[€$£]\s?\d", analysis_text) +
            _findall(r"\d[\.,]\d+%|\bpercentuale\b", analysis_text)
        )
        score += 0.2 * generic_signals

    return score

# ---------------------------------------------------------------------------
# Entry point: scelta del prompt
# ---------------------------------------------------------------------------

def choose_prompt(file_name: str, analysis_text: str) -> Tuple[str, str, dict]:
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
```

### Come usarlo nel tuo flusso

```python
from prompt_router import choose_prompt
# analysis_text lo ottieni dal preprocessing (con tagging [p. X] ecc.)
prompt_name, prompt_text, debug = choose_prompt(file_name="Bilancio_2024.pdf", analysis_text=analysis_text)

print("Scelto:", prompt_name)
# Invia prompt_text al modello LLM
# llm_response = model.generate(prompt_text)
```

### Note pratiche

* Il router è **deterministico e trasparente** (niente chiamate a LLM per la classificazione).
* Se vuoi più precisione, puoi:

  1. aggiungere parole-chiave/pattern alla casistica;
  2. alzare/abbassare `min_score_to_win`;
  3. creare prompt ulteriori (es. **budget**, **ordini d’acquisto**, **HR**…).
* In caso di documenti misti (es. report mensile con sezione vendite + magazzino), puoi eseguire il router **per chunk** (vedi il preprocessore che abbiamo fatto) e poi **fondere** i risultati.
