"""Helper functions for formatting analysis results."""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def format_analysis_result(raw_response: str) -> str:
    """
    Formatta il risultato dell'analisi per una migliore leggibilità.

    Args:
        raw_response: La risposta grezza dal LLM contenente JSON e sintesi

    Returns:
        Una stringa formattata in markdown per Streamlit
    """
    try:
        # Debug logging
        logger.debug(f"format_analysis_result called with response length: {len(raw_response) if raw_response else 0}")
        
        # Estrai il tipo di analisi
        analysis_type_match = re.search(r"\[Analisi tipo: (\w+)\]", raw_response)
        analysis_type = analysis_type_match.group(1) if analysis_type_match else "GENERALE"
        logger.info(f"Analysis type detected: {analysis_type}")

        # Estrai la sezione JSON
        json_match = re.search(r"<(?:KPI_)?JSON>(.*?)</(?:KPI_)?JSON>", raw_response, re.DOTALL)
        json_data = None
        if json_match:
            try:
                # Pulisci il JSON rimuovendo spazi extra e newline
                json_str = json_match.group(1).strip()
                logger.debug(f"JSON string length: {len(json_str)}")
                json_data = json.loads(json_str)
                logger.info(f"JSON parsed successfully, keys: {list(json_data.keys()) if json_data else []}")
            except json.JSONDecodeError as e:
                logger.warning(f"Errore parsing JSON: {e}")
                logger.debug(f"Failed JSON string (first 500 chars): {json_str[:500] if json_str else 'empty'}")
                json_data = None
        else:
            logger.warning("No JSON section found in response")

        # Estrai la sintesi
        summary_match = re.search(r"<SINTESI>(.*?)</SINTESI>", raw_response, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""
        logger.debug(f"Summary extracted, length: {len(summary)}")

        # Costruisci l'output formattato
        formatted_parts = []

        # Header con tipo di analisi
        formatted_parts.append(f"## Analisi {analysis_type.capitalize()}\n")

        # Formatta in base al tipo di analisi
        if analysis_type == "BILANCIO" and json_data:
            formatted_parts.append(_format_bilancio(json_data))
        elif analysis_type == "FATTURATO" and json_data:
            formatted_parts.append(_format_fatturato(json_data))
        elif analysis_type == "MAGAZZINO" and json_data:
            formatted_parts.append(_format_magazzino(json_data))
        elif analysis_type == "CONTRATTO" and json_data:
            formatted_parts.append(_format_contratto(json_data))
        elif analysis_type == "PRESENTAZIONE" and json_data:
            formatted_parts.append(_format_presentazione(json_data))
        elif analysis_type == "SCADENZARIO" and json_data:
            formatted_parts.append(_format_scadenzario(json_data))
        elif json_data:
            formatted_parts.append(_format_generale(json_data))

        # Aggiungi la sintesi
        if summary:
            formatted_parts.append("\n### Sintesi Esecutiva\n")
            formatted_parts.append(summary)

        # Assicurati che tutte le parti siano stringhe
        clean_parts = []
        for part in formatted_parts:
            if isinstance(part, str):
                clean_parts.append(part)
            else:
                clean_parts.append(str(part))

        return "\n".join(clean_parts)

    except Exception as e:
        logger.error(f"Errore nella formattazione: {str(e)}")
        logger.debug(f"Raw response che ha causato l'errore: {raw_response[:500]}")

        # Prova un formatting minimo ma comunque migliore del raw
        try:
            # Estrai almeno la sintesi se possibile
            summary_match = re.search(r"<SINTESI>(.*?)</SINTESI>", raw_response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
                analysis_type_match = re.search(r"\[Analisi tipo: (\w+)\]", raw_response)
                analysis_type = analysis_type_match.group(1).capitalize() if analysis_type_match else "Documento"

                return f"## Analisi {analysis_type}\n\n### Sintesi Esecutiva\n\n{summary}\n\n---\n\n*Nota: Alcuni dettagli tecnici potrebbero non essere visualizzati correttamente*"
        except Exception:
            pass

        # Fallback finale - almeno rimuovi il formato raw grezzo
        clean_text = raw_response.replace("[Analisi tipo: ", "**Tipo Analisi:** ").replace("]", "")
        clean_text = re.sub(r"</?(?:KPI_)?JSON>", "", clean_text)
        clean_text = re.sub(r"</?SINTESI>", "### Sintesi\n", clean_text)

        return f"### Risultato Analisi\n\n{clean_text}"


def _format_bilancio(data: dict[str, Any]) -> str:
    """Formatta i dati di bilancio."""
    parts = []

    # Periodi coperti
    if data.get("periodi_coperti"):
        # Handle both list of strings and list of dicts
        if data["periodi_coperti"] and isinstance(data["periodi_coperti"][0], dict):
            periodo_strings = []
            for p in data["periodi_coperti"]:
                if isinstance(p, dict):
                    # Format dict as readable string
                    periodo_str = f"{p.get('mese', '')} {p.get('anno', '')} {p.get('tipo', '')}".strip()
                    if periodo_str:
                        periodo_strings.append(periodo_str)
                else:
                    periodo_strings.append(str(p))
            if periodo_strings:
                parts.append(f"**Periodi analizzati:** {', '.join(periodo_strings)}\n")
        else:
            parts.append(f"**Periodi analizzati:** {', '.join(map(str, data['periodi_coperti']))}\n")

    # Conto Economico
    if data.get("conto_economico"):
        parts.append("### Conto Economico\n")
        ce = data["conto_economico"]

        if ce.get("ricavi"):
            for r in ce["ricavi"]:
                if r.get("valore"):
                    parts.append(
                        f"- **Ricavi ({r.get('periodo', 'N/D')}):** {_format_currency(r['valore'])} {r.get('unita', '€')}"
                    )

        if ce.get("ebitda"):
            for e in ce["ebitda"]:
                if e.get("valore"):
                    parts.append(
                        f"- **EBITDA ({e.get('periodo', 'N/D')}):** {_format_currency(e['valore'])} {e.get('unita', '€')}"
                    )

        if ce.get("ebit"):
            for e in ce["ebit"]:
                if e.get("valore"):
                    parts.append(
                        f"- **EBIT ({e.get('periodo', 'N/D')}):** {_format_currency(e['valore'])} {e.get('unita', '€')}"
                    )

        if ce.get("utile_netto"):
            for u in ce["utile_netto"]:
                if u.get("valore"):
                    parts.append(
                        f"- **Utile Netto ({u.get('periodo', 'N/D')}):** {_format_currency(u['valore'])} {u.get('unita', '€')}"
                    )

        parts.append("")

    # Margini e Ratios
    if data.get("margini_e_ratios"):
        parts.append("### Margini e Indicatori\n")
        for ratio in data["margini_e_ratios"]:
            if ratio.get("valore"):
                parts.append(f"- **{ratio.get('nome', 'N/D')}:** {ratio['valore']}{ratio.get('unita', '')}")
        parts.append("")

    # Stato Patrimoniale (se presente)
    sp = data.get("stato_patrimoniale", {})
    has_sp_data = any([sp.get("cassa_e_equivalenti"), sp.get("debito_finanziario_totale"), sp.get("patrimonio_netto")])

    if has_sp_data:
        parts.append("### Stato Patrimoniale\n")

        if sp.get("cassa_e_equivalenti"):
            for c in sp["cassa_e_equivalenti"]:
                if c.get("valore"):
                    parts.append(f"- **Cassa:** {_format_currency(c['valore'])} {c.get('unita', '€')}")

        if sp.get("debito_finanziario_totale"):
            for d in sp["debito_finanziario_totale"]:
                if d.get("valore"):
                    parts.append(f"- **Debito Totale:** {_format_currency(d['valore'])} {d.get('unita', '€')}")

        if sp.get("patrimonio_netto"):
            for p in sp["patrimonio_netto"]:
                if p.get("valore"):
                    parts.append(f"- **Patrimonio Netto:** {_format_currency(p['valore'])} {p.get('unita', '€')}")

        parts.append("")

    # Rischi (se presenti)
    if data.get("rischi"):
        parts.append("### Rischi Identificati\n")
        for rischio in data["rischi"]:
            if rischio.get("descrizione"):
                impact = f" - Impatto: {rischio['impatto']}" if rischio.get("impatto") else ""
                parts.append(f"- {rischio['descrizione']}{impact}")
        parts.append("")

    return "\n".join(parts)


def _format_fatturato(data: dict[str, Any]) -> str:
    """Formatta i dati di fatturato/vendite."""
    parts = []

    # Periodi coperti
    if data.get("periodi_coperti"):
        # Handle both list of strings and list of dicts
        if data["periodi_coperti"] and isinstance(data["periodi_coperti"][0], dict):
            periodo_strings = []
            for p in data["periodi_coperti"]:
                if isinstance(p, dict):
                    # Format dict as readable string
                    periodo_str = f"{p.get('mese', '')} {p.get('anno', '')} {p.get('tipo', '')}".strip()
                    if periodo_str:
                        periodo_strings.append(periodo_str)
                else:
                    periodo_strings.append(str(p))
            if periodo_strings:
                parts.append(f"**Periodi analizzati:** {', '.join(periodo_strings)}\n")
        else:
            parts.append(f"**Periodi analizzati:** {', '.join(map(str, data['periodi_coperti']))}\n")

    # Fatturato totale
    if data.get("fatturato_totale"):
        parts.append("### Fatturato\n")
        for f in data["fatturato_totale"]:
            if f.get("valore"):
                var_yoy = f" ({f['var_yoy']} YoY)" if f.get("var_yoy") else ""
                parts.append(
                    f"- **{f.get('periodo', 'Totale')}:** {_format_currency(f['valore'])} {f.get('valuta', '€')}{var_yoy}"
                )
        parts.append("")

    # Ripartizione
    ripart = data.get("ripartizione", {})
    if ripart.get("per_prodotto") or ripart.get("per_cliente") or ripart.get("per_area"):
        parts.append("### Ripartizione Vendite\n")

        if ripart.get("per_prodotto"):
            parts.append("**Per Prodotto:**")
            for p in ripart["per_prodotto"]:
                if p.get("valore"):
                    parts.append(
                        f"- {p.get('prodotto', 'N/D')}: {_format_currency(p['valore'])} {p.get('valuta', '€')}"
                    )

        if ripart.get("per_cliente"):
            parts.append("\n**Per Cliente:**")
            for c in ripart["per_cliente"]:
                if c.get("valore"):
                    parts.append(f"- {c.get('cliente', 'N/D')}: {_format_currency(c['valore'])} {c.get('valuta', '€')}")

        if ripart.get("per_area"):
            parts.append("\n**Per Area:**")
            for a in ripart["per_area"]:
                if a.get("valore"):
                    parts.append(f"- {a.get('area', 'N/D')}: {_format_currency(a['valore'])} {a.get('valuta', '€')}")

        parts.append("")

    # KPI Vendite
    if data.get("kpi_vendite"):
        parts.append("### KPI Vendite\n")
        for kpi in data["kpi_vendite"]:
            if kpi.get("valore"):
                parts.append(f"- **{kpi.get('nome', 'N/D')}:** {kpi['valore']} {kpi.get('unita', '')}")
        parts.append("")

    # Pipeline e Forecast
    if data.get("pipeline_e_forecast"):
        parts.append("### Pipeline e Previsioni\n")
        for p in data["pipeline_e_forecast"]:
            if p.get("valore_forecast"):
                parts.append(f"- **{p.get('periodo', 'N/D')}:** {_format_currency(p['valore_forecast'])}")
                if p.get("assunzioni"):
                    parts.append(f"  - Assunzioni: {p['assunzioni']}")
        parts.append("")

    return "\n".join(parts)


def _format_magazzino(data: dict[str, Any]) -> str:
    """Formatta i dati di magazzino."""
    parts = []

    # Giacenze totali
    if data.get("giacenze_totali"):
        parts.append("### Giacenze\n")
        for g in data["giacenze_totali"]:
            if g.get("valore"):
                giorni = f" ({g['giorni_giacenza']} giorni)" if g.get("giorni_giacenza") else ""
                parts.append(
                    f"- **{g.get('periodo', 'Totale')}:** {_format_currency(g['valore'])} {g.get('unita', '€')}{giorni}"
                )
        parts.append("")

    # KPI Logistici
    if data.get("kpi_logistici"):
        parts.append("### KPI Logistici\n")
        for kpi in data["kpi_logistici"]:
            if kpi.get("valore_pct"):
                parts.append(f"- **{kpi.get('nome', 'N/D')}:** {kpi['valore_pct']}%")
        parts.append("")

    # Rotazione magazzino
    if data.get("rotazione_magazzino"):
        parts.append("### Rotazione\n")
        for r in data["rotazione_magazzino"]:
            if r.get("indice_rotazione"):
                parts.append(f"- **{r.get('periodo', 'N/D')}:** {r['indice_rotazione']}{r.get('unita', 'x')}")
        parts.append("")

    # Eccessi e obsoleti
    if data.get("eccessi_e_obsoleti"):
        parts.append("### Scorte Problematiche\n")
        for e in data["eccessi_e_obsoleti"]:
            if e.get("valore"):
                pct = f" ({e['percentuale_su_scorte']}%)" if e.get("percentuale_su_scorte") else ""
                parts.append(
                    f"- {e.get('sku_o_categoria', 'N/D')}: {_format_currency(e['valore'])} {e.get('valuta', '€')}{pct}"
                )
        parts.append("")

    return "\n".join(parts)


def _format_contratto(data: dict[str, Any]) -> str:
    """Formatta i dati di contratto."""
    parts = []

    # Parti coinvolte
    if data.get("parti_coinvolte"):
        parts.append("### Parti Coinvolte\n")
        for p in data["parti_coinvolte"]:
            if p.get("nome"):
                ruolo = f" ({p['ruolo']})" if p.get("ruolo") else ""
                parts.append(f"- {p['nome']}{ruolo}")
        parts.append("")

    # Oggetto e ambito
    if data.get("oggetto_e_ambito", {}).get("testo"):
        parts.append("### Oggetto del Contratto\n")
        parts.append(data["oggetto_e_ambito"]["testo"])
        parts.append("")

    # Durata
    if data.get("durata_e_decorrenza"):
        d = data["durata_e_decorrenza"]
        parts.append("### Durata\n")
        if d.get("inizio"):
            parts.append(f"- **Inizio:** {d['inizio']}")
        if d.get("fine"):
            parts.append(f"- **Fine:** {d['fine']}")
        if d.get("rinnovo"):
            parts.append(f"- **Rinnovo:** {d['rinnovo']}")
        parts.append("")

    # Corrispettivi
    if data.get("corrispettivi_e_pagamenti"):
        parts.append("### Corrispettivi e Pagamenti\n")
        for c in data["corrispettivi_e_pagamenti"]:
            if c.get("importo"):
                parts.append(
                    f"- {c.get('descrizione', 'N/D')}: {_format_currency(c['importo'])} {c.get('valuta', '€')}"
                )
                if c.get("scadenza"):
                    parts.append(f"  - Scadenza: {c['scadenza']}")
        parts.append("")

    # KPI/SLA/Penali
    if data.get("kpi_sla_penali"):
        parts.append("### SLA e Penali\n")
        for k in data["kpi_sla_penali"]:
            if k.get("kpi"):
                soglia = f" - Soglia: {k['soglia']}" if k.get("soglia") else ""
                penale = f" - Penale: {k['penale']}" if k.get("penale") else ""
                parts.append(f"- **{k['kpi']}**{soglia}{penale}")
        parts.append("")

    # Legge applicabile
    if data.get("legge_applicabile_forum"):
        legal_info = data["legge_applicabile_forum"]
        if legal_info.get("legge") or legal_info.get("foro"):
            parts.append("### Aspetti Legali\n")
            if legal_info.get("legge"):
                parts.append(f"- **Legge Applicabile:** {legal_info['legge']}")
            if legal_info.get("foro"):
                parts.append(f"- **Foro Competente:** {legal_info['foro']}")
            parts.append("")

    return "\n".join(parts)


def _format_presentazione(data: dict[str, Any]) -> str:
    """Formatta i dati di presentazione."""
    parts = []

    # Info base
    if data.get("titolo_presentazione"):
        parts.append(f"**Titolo:** {data['titolo_presentazione']}\n")
    if data.get("autore_o_azienda"):
        parts.append(f"**Autore:** {data['autore_o_azienda']}\n")
    if data.get("data_presentazione"):
        parts.append(f"**Data:** {data['data_presentazione']}\n")

    # Obiettivo principale
    if data.get("obiettivo_principale"):
        parts.append(f"### Obiettivo Principale\n{data['obiettivo_principale']}\n")

    # Messaggi chiave
    if data.get("messaggi_chiave"):
        parts.append("### Messaggi Chiave\n")
        for m in data["messaggi_chiave"]:
            if m.get("messaggio"):
                parts.append(f"- {m['messaggio']}")
                if m.get("supporto_dati"):
                    parts.append(f"  - Dati: {m['supporto_dati']}")
        parts.append("")

    # Dati e metriche
    if data.get("dati_e_metriche"):
        parts.append("### Dati e Metriche\n")
        for d in data["dati_e_metriche"]:
            if d.get("metrica") and d.get("valore"):
                periodo = f" ({d['periodo']})" if d.get("periodo") else ""
                trend = f" - Trend: {d['trend']}" if d.get("trend") else ""
                parts.append(f"- **{d['metrica']}:** {d['valore']}{periodo}{trend}")
        parts.append("")

    # Next steps
    if data.get("next_steps"):
        parts.append("### Prossimi Passi\n")
        for n in data["next_steps"]:
            if n.get("azione"):
                timeline = f" - {n['timeline']}" if n.get("timeline") else ""
                responsabile = f" ({n['responsabile']})" if n.get("responsabile") else ""
                parts.append(f"- {n['azione']}{timeline}{responsabile}")
        parts.append("")

    return "\n".join(parts)


def _format_scadenzario(data: dict[str, Any]) -> str:
    """Formatta i dati dello scadenzario crediti."""
    parts = []

    # Periodi coperti
    if data.get("periodi_coperti"):
        if data["periodi_coperti"] and isinstance(data["periodi_coperti"][0], dict):
            periodo_strings = []
            for p in data["periodi_coperti"]:
                if isinstance(p, dict):
                    periodo_str = f"{p.get('mese', '')} {p.get('anno', '')} {p.get('tipo', '')}".strip()
                    if periodo_str:
                        periodo_strings.append(periodo_str)
                else:
                    periodo_strings.append(str(p))
            if periodo_strings:
                parts.append(f"**Periodi analizzati:** {', '.join(periodo_strings)}\n")
        else:
            parts.append(f"**Periodi analizzati:** {', '.join(map(str, data['periodi_coperti']))}\n")

    # Perimetro e valute
    if data.get("perimetro"):
        parts.append(f"**Perimetro:** {data['perimetro']}\n")
    if data.get("valute"):
        parts.append(f"**Valute:** {', '.join(data['valute'])}\n")

    # Totali
    if data.get("totali"):
        parts.append("### Totali Crediti\n")
        totali = data["totali"]

        if totali.get("crediti_lordi"):
            for c in totali["crediti_lordi"]:
                if c.get("valore"):
                    parts.append(
                        f"- **Crediti Lordi ({c.get('periodo', 'N/D')}):** {_format_currency(c['valore'])} {c.get('unita', 'EUR')}"
                    )

        if totali.get("fondo_svalutazione"):
            for f in totali["fondo_svalutazione"]:
                if f.get("valore"):
                    parts.append(
                        f"- **Fondo Svalutazione ({f.get('periodo', 'N/D')}):** {_format_currency(f['valore'])} {f.get('unita', 'EUR')}"
                    )

        if totali.get("crediti_netto"):
            for n in totali["crediti_netto"]:
                if n.get("valore"):
                    parts.append(
                        f"- **Crediti Netto ({n.get('periodo', 'N/D')}):** {_format_currency(n['valore'])} {n.get('unita', 'EUR')}"
                    )

        if totali.get("numero_clienti_attivi"):
            for n in totali["numero_clienti_attivi"]:
                if n.get("valore"):
                    parts.append(f"- **Clienti Attivi:** {n['valore']}")
        parts.append("")

    # Aging Bucket
    if data.get("aging_bucket"):
        parts.append("### Aging Crediti\n")
        for bucket in data["aging_bucket"]:
            if bucket.get("valore") or bucket.get("percentuale_su_totale"):
                valore = (
                    f"{_format_currency(bucket['valore'])} {bucket.get('unita', 'EUR')}" if bucket.get("valore") else ""
                )
                percentuale = (
                    f" ({bucket['percentuale_su_totale']}{bucket.get('unita_percent', '%')})"
                    if bucket.get("percentuale_su_totale")
                    else ""
                )
                parts.append(f"- **{bucket.get('bucket', 'N/D')}:** {valore}{percentuale}")
        parts.append("")

    # Past Due
    if data.get("past_due"):
        pd = data["past_due"]
        if pd.get("totale_scaduto") or pd.get("dpd_medio_ponderato") or pd.get("percentuale_scaduto_su_totale"):
            parts.append("### Crediti Scaduti\n")

            if pd.get("totale_scaduto"):
                for t in pd["totale_scaduto"]:
                    if t.get("valore"):
                        parts.append(f"- **Totale Scaduto:** {_format_currency(t['valore'])} {t.get('unita', 'EUR')}")

            if pd.get("dpd_medio_ponderato"):
                for d in pd["dpd_medio_ponderato"]:
                    if d.get("valore"):
                        parts.append(f"- **DPD Medio Ponderato:** {d['valore']} giorni")

            if pd.get("percentuale_scaduto_su_totale"):
                for p in pd["percentuale_scaduto_su_totale"]:
                    if p.get("valore"):
                        parts.append(f"- **% Scaduto su Totale:** {p['valore']}%")
            parts.append("")

    # KPI
    if data.get("kpi"):
        kpi = data["kpi"]
        parts.append("### KPI Principali\n")

        if kpi.get("dso"):
            for d in kpi["dso"]:
                if d.get("valore"):
                    metodo = f" (Metodo: {d['metodo']})" if d.get("metodo") else ""
                    parts.append(
                        f"- **DSO ({d.get('periodo', 'N/D')}):** {d['valore']} {d.get('unita', 'giorni')}{metodo}"
                    )

        if kpi.get("turnover_crediti"):
            for t in kpi["turnover_crediti"]:
                if t.get("valore"):
                    parts.append(f"- **Turnover Crediti:** {t['valore']}x")

        if kpi.get("dpd_>90gg_percent"):
            for p in kpi["dpd_>90gg_percent"]:
                if p.get("valore"):
                    parts.append(f"- **DPD >90gg:** {p['valore']}%")
        parts.append("")

    # Concentrazione Rischio
    if data.get("concentrazione_rischio"):
        conc = data["concentrazione_rischio"]
        has_concentration = any(
            [
                conc.get("top1_percent_su_totale"),
                conc.get("top5_percent_su_totale"),
                conc.get("top10_percent_su_totale"),
                conc.get("primi_clienti"),
            ]
        )

        if has_concentration:
            parts.append("### Concentrazione Rischio\n")

            if conc.get("top1_percent_su_totale"):
                for t in conc["top1_percent_su_totale"]:
                    if t.get("valore"):
                        parts.append(f"- **Top 1 Cliente:** {t['valore']}% del totale")

            if conc.get("top5_percent_su_totale"):
                for t in conc["top5_percent_su_totale"]:
                    if t.get("valore"):
                        parts.append(f"- **Top 5 Clienti:** {t['valore']}% del totale")

            if conc.get("top10_percent_su_totale"):
                for t in conc["top10_percent_su_totale"]:
                    if t.get("valore"):
                        parts.append(f"- **Top 10 Clienti:** {t['valore']}% del totale")

            if conc.get("primi_clienti"):
                parts.append("\n**Principali Clienti:**")
                for cliente in conc["primi_clienti"]:
                    if cliente.get("cliente"):
                        valore = (
                            f": {_format_currency(cliente['valore'])} {cliente.get('unita', 'EUR')}"
                            if cliente.get("valore")
                            else ""
                        )
                        percentuale = (
                            f" ({cliente['percentuale_su_totale']}{cliente.get('unita_percent', '%')})"
                            if cliente.get("percentuale_su_totale")
                            else ""
                        )
                        parts.append(f"- {cliente['cliente']}{valore}{percentuale}")
            parts.append("")

    # Qualità Crediti
    if data.get("qualita_crediti"):
        qual = data["qualita_crediti"]
        has_quality = any(
            [
                qual.get("posizioni_in_contenzioso"),
                qual.get("piani_rientro_e_promesse_pagamento"),
                qual.get("garanzie_collaterali"),
                qual.get("write_off"),
                qual.get("coverage_fondo_su_scaduto"),
            ]
        )

        if has_quality:
            parts.append("### Qualità del Credito\n")

            if qual.get("posizioni_in_contenzioso"):
                for p in qual["posizioni_in_contenzioso"]:
                    if p.get("numero") or p.get("valore"):
                        numero = f"{p['numero']} posizioni" if p.get("numero") else ""
                        valore = (
                            f" - {_format_currency(p['valore'])} {p.get('unita', 'EUR')}" if p.get("valore") else ""
                        )
                        parts.append(f"- **Contenziosi:** {numero}{valore}")

            if qual.get("piani_rientro_e_promesse_pagamento"):
                for p in qual["piani_rientro_e_promesse_pagamento"]:
                    if p.get("numero") or p.get("importo"):
                        numero = f"{p['numero']} piani" if p.get("numero") else ""
                        importo = (
                            f" - {_format_currency(p['importo'])} {p.get('unita', 'EUR')}" if p.get("importo") else ""
                        )
                        parts.append(f"- **Piani di Rientro:** {numero}{importo}")

            if qual.get("garanzie_collaterali"):
                for g in qual["garanzie_collaterali"]:
                    if g.get("copertura_portafoglio_percentuale"):
                        parts.append(
                            f"- **Garanzie Collaterali:** {g['copertura_portafoglio_percentuale']}% del portafoglio"
                        )
                    elif g.get("valore"):
                        parts.append(
                            f"- **Garanzie Collaterali:** {_format_currency(g['valore'])} {g.get('unita', 'EUR')}"
                        )

            if qual.get("write_off"):
                for w in qual["write_off"]:
                    if w.get("valore"):
                        parts.append(
                            f"- **Write-off ({w.get('periodo', 'N/D')}):** {_format_currency(w['valore'])} {w.get('unita', 'EUR')}"
                        )

            if qual.get("coverage_fondo_su_scaduto"):
                for c in qual["coverage_fondo_su_scaduto"]:
                    if c.get("valore"):
                        parts.append(f"- **Coverage Fondo su Scaduto:** {c['valore']}%")
            parts.append("")

    # Note
    if data.get("note"):
        parts.append(f"### Note\n{data['note']}\n")

    return "\n".join(parts)


def _format_generale(data: dict[str, Any]) -> str:
    """Formatta i dati generici."""
    parts = []

    # Tipo e oggetto
    if data.get("tipo_documento"):
        parts.append(f"**Tipo Documento:** {data['tipo_documento']}\n")
    if data.get("oggetto_principale"):
        parts.append(f"**Oggetto:** {data['oggetto_principale']}\n")

    # Elementi chiave
    if data.get("elementi_chiave"):
        parts.append("### Elementi Chiave\n")
        for e in data["elementi_chiave"]:
            if e.get("punto"):
                fonte = f" (pag. {e['fonte_pagina']})" if e.get("fonte_pagina") else ""
                parts.append(f"- {e['punto']}{fonte}")
        parts.append("")

    # Dati quantitativi
    if data.get("dati_quantitativi"):
        parts.append("### Dati Quantitativi\n")
        for d in data["dati_quantitativi"]:
            if d.get("descrizione") and d.get("valore"):
                periodo = f" ({d['periodo_riferimento']})" if d.get("periodo_riferimento") else ""
                fonte = f" - pag. {d['fonte_pagina']}" if d.get("fonte_pagina") else ""
                parts.append(f"- **{d['descrizione']}:** {d['valore']} {d.get('unita', '')}{periodo}{fonte}")
        parts.append("")

    # Date rilevanti
    if data.get("date_rilevanti"):
        parts.append("### Date Importanti\n")
        for d in data["date_rilevanti"]:
            if d.get("evento") and d.get("data_iso"):
                fonte = f" (pag. {d['fonte_pagina']})" if d.get("fonte_pagina") else ""
                parts.append(f"- **{d['evento']}:** {d['data_iso']}{fonte}")
        parts.append("")

    # Conclusioni
    if data.get("conclusioni_o_raccomandazioni"):
        parts.append("### Conclusioni e Raccomandazioni\n")
        for c in data["conclusioni_o_raccomandazioni"]:
            if c.get("testo"):
                fonte = f" (pag. {c['fonte_pagina']})" if c.get("fonte_pagina") else ""
                parts.append(f"- {c['testo']}{fonte}")
        parts.append("")

    return "\n".join(parts)


def _format_currency(value: str) -> str:
    """
    Formatta un valore monetario per una migliore leggibilità.

    Args:
        value: Stringa contenente il valore (può avere punti come separatori)

    Returns:
        Valore formattato con separatori di migliaia
    """
    try:
        # Rimuovi spazi e converti virgole in punti
        clean_value = value.replace(" ", "").replace(",", ".")

        # Prova a convertire in float
        if "." in clean_value:
            # Se c'è un punto, potrebbe essere decimale o separatore di migliaia
            parts = clean_value.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                # Probabilmente è un separatore di migliaia (es: 5.214.095)
                clean_value = clean_value.replace(".", "")

        num = float(clean_value)

        # Formatta con separatori di migliaia
        if num >= 1000000:
            return f"{num / 1000000:,.1f}M".replace(",", ".")
        elif num >= 1000:
            return f"{num:,.0f}".replace(",", ".")
        else:
            return f"{num:,.2f}".replace(",", ".")

    except (ValueError, AttributeError):
        # Se non riesci a convertire, ritorna il valore originale
        return str(value)


def extract_structured_data(raw_response: str) -> Optional[dict[str, Any]]:
    """
    Estrae solo i dati strutturati JSON dalla risposta.

    Args:
        raw_response: La risposta grezza dal LLM

    Returns:
        Il dizionario JSON estratto o None se non trovato
    """
    try:
        json_match = re.search(r"<(?:KPI_)?JSON>(.*?)</(?:KPI_)?JSON>", raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            return json.loads(json_str)
    except Exception as e:
        logger.error(f"Errore nell'estrazione JSON: {str(e)}")

    return None


def extract_summary(raw_response: str) -> Optional[str]:
    """
    Estrae solo la sintesi dalla risposta.

    Args:
        raw_response: La risposta grezza dal LLM

    Returns:
        La sintesi estratta o None se non trovata
    """
    try:
        summary_match = re.search(r"<SINTESI>(.*?)</SINTESI>", raw_response, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
    except Exception as e:
        logger.error(f"Errore nell'estrazione della sintesi: {str(e)}")

    return None
