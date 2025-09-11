"""LLM Service for intelligent analysis and insights generation."""

import json
import logging
from typing import Any, Optional

from openai import OpenAI

from config.settings import settings
from services.prompt_router import choose_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-based analysis and natural language generation."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens

    def generate_business_insights(self, csv_analysis: dict[str, Any], rag_context: Optional[str] = None, document_name: Optional[str] = None) -> str:
        """Generate comprehensive business insights from analysis data."""
        try:
            # Prepare the prompt
            prompt = self._build_insights_prompt(csv_analysis, rag_context, document_name)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un analista aziendale senior italiano che fornisce approfondimenti strategici basati su dati finanziari e documenti aziendali. Fornisci raccomandazioni chiare e attuabili. CRITICO: Devi rispondere ESCLUSIVAMENTE in lingua italiana. Non utilizzare MAI termini inglesi. Traduci tutti i concetti business in italiano (es. 'revenue' = 'fatturato', 'growth' = 'crescita', 'performance' = 'prestazioni', ecc.).",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return f"Unable to generate insights: {str(e)}"

    def _build_insights_prompt(self, csv_analysis: dict[str, Any], rag_context: Optional[str], document_name: Optional[str] = None) -> str:
        """Build comprehensive prompt for insights generation."""
        prompt_parts = ["Per favore analizza i seguenti dati aziendali e fornisci approfondimenti strategici:\n"]

        # Add CSV analysis data
        if "summary" in csv_analysis:
            prompt_parts.append("\n## Metriche Finanziarie:")
            for key, value in csv_analysis["summary"].items():
                prompt_parts.append(f"- {key}: {value}")

        if "trends" in csv_analysis:
            prompt_parts.append("\n## Tendenze:")
            if "yoy_growth" in csv_analysis["trends"]:
                for growth in csv_analysis["trends"]["yoy_growth"]:
                    prompt_parts.append(
                        f"- Anno {growth['year']}: {growth['growth_percentage']}% crescita "
                        f"(variazione: {growth['absolute_change']:,.2f})"
                    )

        if "ratios" in csv_analysis:
            prompt_parts.append("\n## Rapporti Finanziari:")
            for ratio, value in csv_analysis["ratios"].items():
                prompt_parts.append(f"- {ratio}: {value}%")

        if "insights" in csv_analysis:
            prompt_parts.append("\n## Osservazioni Iniziali:")
            for insight in csv_analysis["insights"]:
                prompt_parts.append(f"- {insight}")

        # Add RAG context if available
        if rag_context:
            prompt_parts.append(f"\n## Contesto Aggiuntivo dai Documenti:\n{rag_context}")

        prompt_parts.append("""

IMPORTANTE: Rispondi ESCLUSIVAMENTE in italiano. Non usare MAI termini inglesi.

Per favore fornisci:
1. **Riepilogo Esecutivo** (2-3 frasi in italiano)
2. **Punti di Forza Chiave** (3 punti elenco in italiano)
3. **Aree di Preoccupazione** (3 punti elenco in italiano)
4. **Raccomandazioni Strategiche** (5 azioni specifiche in italiano)
5. **Valutazione del Rischio** (in italiano)
6. **Prospettive a 12 Mesi** (in italiano)

NON utilizzare mai termini come: "Executive Summary", "Key Strengths", "Growth", "Revenue", "Performance", ecc.
Usa sempre la traduzione italiana: "Riepilogo Esecutivo", "Punti di Forza", "Crescita", "Fatturato", "Prestazioni", ecc.
        """)

        return "\n".join(prompt_parts)

    def compare_periods_narrative(self, comparison_data: dict[str, Any]) -> str:
        """Generate narrative comparison between periods."""
        try:
            prompt = self._build_comparison_prompt(comparison_data)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un analista finanziario che spiega i cambiamenti periodo su periodo nelle metriche aziendali. IMPORTANTE: Rispondi SEMPRE in italiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens // 2,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating comparison narrative: {str(e)}")
            return "Unable to generate comparison narrative."

    def _build_comparison_prompt(self, comparison_data: dict[str, Any]) -> str:
        """Build prompt for period comparison."""
        prompt_parts = ["Analizza il seguente confronto tra periodi:\n"]

        if "differences" in comparison_data:
            prompt_parts.append("\n## Variazioni Assolute:")
            for metric, diff in comparison_data["differences"].items():
                prompt_parts.append(f"- {metric}: {diff:+,.2f}")

        if "percentage_changes" in comparison_data:
            prompt_parts.append("\n## Variazioni Percentuali:")
            for metric, pct in comparison_data["percentage_changes"].items():
                prompt_parts.append(f"- {metric}: {pct:+.1f}%")

        prompt_parts.append("""

Per favore fornisci una narrazione chiara e concisa che:
1. Evidenzi i cambiamenti più significativi
2. Spieghi le cause potenziali
3. Identifichi modelli o correlazioni
4. Suggerisca implicazioni per il business
        """)

        return "\n".join(prompt_parts)

    def answer_business_question(self, question: str, context: dict[str, Any]) -> str:
        """Answer specific business questions using available context."""
        try:
            # Build context-aware prompt
            context_str = json.dumps(context, indent=2, default=str)

            prompt = f"""
Basandoti sui seguenti dati e analisi aziendali:

{context_str}

Domanda: {question}

Per favore fornisci una risposta dettagliata e basata sui dati che:
1. Risponda direttamente alla domanda
2. Faccia riferimento a metriche specifiche dai dati
3. Fornisca approfondimenti attuabili dove rilevante
4. Riconosca eventuali limitazioni nei dati disponibili
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un esperto di business intelligence. Rispondi alle domande con precisione usando i dati forniti, e dichiara chiaramente quando le informazioni sono insufficienti. IMPORTANTE: Rispondi SEMPRE in italiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Unable to process question: {str(e)}"

    def generate_executive_report(
        self,
        csv_analysis: dict[str, Any],
        rag_insights: Optional[str] = None,
        custom_sections: Optional[list[str]] = None,
    ) -> str:
        """Generate comprehensive executive report."""
        try:
            sections = custom_sections or [
                "Riepilogo Esecutivo",
                "Performance Finanziaria",
                "Evidenze Operative",
                "Posizione di Mercato",
                "Raccomandazioni",
                "Prossimi Passi",
            ]

            prompt = f"""
Genera un report esecutivo professionale basato sui seguenti dati:

## Analisi Finanziaria:
{json.dumps(csv_analysis, indent=2, default=str)}

## Approfondimenti dai Documenti:
{rag_insights or "Nessun contesto documentale aggiuntivo disponibile"}

Per favore crea un report completo con queste sezioni:
{chr(10).join(f"- {section}" for section in sections)}

IMPORTANTE: Scrivi tutto il report in italiano perfetto. Non usare MAI termini inglesi.

Formatta il report in modo professionale con intestazioni chiare e punti elenco dove appropriato.
Includi metriche e percentuali specifiche per supportare tutte le affermazioni.
Usa terminologia aziendale italiana (fatturato, crescita, prestazioni, margini, ecc.)
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un consulente esecutivo di livello C che prepara report strategici per le riunioni del consiglio. Sii conciso ma completo, basato sui dati e orientato all'azione. IMPORTANTE: Rispondi SEMPRE in italiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature - 0.2,  # Lower temperature for more focused output
                max_tokens=self.max_tokens * 2,  # Allow longer reports
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating executive report: {str(e)}")
            return f"Unable to generate report: {str(e)}"

    def identify_anomalies_explanation(self, anomalies: list[dict[str, Any]]) -> str:
        """Generate explanations for detected anomalies."""
        try:
            if not anomalies:
                return "Nessuna anomalia significativa rilevata nel dataset corrente."

            prompt = f"""
Analizza le seguenti anomalie rilevate nei dati aziendali:

{json.dumps(anomalies, indent=2, default=str)}

Per ogni anomalia, fornisci:
1. Spiegazioni possibili (scenari sia positivi che negativi)
2. Passi di indagine raccomandati
3. Impatto aziendale potenziale
4. Azioni immediate suggerite
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un analista del rischio specializzato nel rilevamento e nell'investigazione di anomalie aziendali. IMPORTANTE: Rispondi SEMPRE in italiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error explaining anomalies: {str(e)}")
            return "Unable to analyze anomalies."

    def generate_action_items(self, analysis: dict[str, Any], priority_count: int = 10) -> list[dict[str, str]]:
        """Generate prioritized action items from analysis."""
        try:
            prompt = f"""
Basandoti su questa analisi aziendale:

{json.dumps(analysis, indent=2, default=str)}

Genera esattamente {priority_count} azioni specifiche e attuabili che l'azienda dovrebbe perseguire.

Formatta la tua risposta come un array JSON con oggetti contenenti:
- "action": azione specifica da intraprendere (in italiano)
- "priority": "alta", "media", o "bassa"
- "timeline": tempistica suggerita (es. "immediato", "30 giorni", "T2 2024")
- "impact": impatto aziendale previsto (in italiano)
- "owner": dipartimento o ruolo suggerito (in italiano)

Concentrati su azioni realistiche e implementabili che affrontino direttamente gli approfondimenti dai dati.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei uno stratega aziendale che crea raccomandazioni attuabili. Restituisci solo JSON valido. IMPORTANTE: Tutti i testi nell'JSON devono essere in italiano.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            # Extract JSON from response
            import re

            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []

        except Exception as e:
            logger.error(f"Error generating action items: {str(e)}")
            return []

    def analyze_document_with_prompt(self, document_text: str, file_name: str) -> dict[str, Any]:
        """Analyze a document using specialized prompt routing."""
        try:
            # Use prompt router to select appropriate prompt
            prompt_name, prompt_text, debug_info = choose_prompt(file_name, document_text)

            logger.info(f"Using specialized prompt '{prompt_name}' for document '{file_name}'")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sei un analista aziendale esperto. Segui esattamente il formato richiesto nel prompt. Rispondi sempre in italiano perfetto.",
                    },
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.2,  # Lower for structured output
                max_tokens=1500,
            )

            content = response.choices[0].message.content

            # Try to extract JSON if present
            json_data = None
            summary = None

            # Extract JSON section
            import re
            json_match = re.search(r"<JSON>(.*?)</JSON>", content, re.DOTALL)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response")

            # Extract summary section
            summary_match = re.search(r"<SINTESI>(.*?)</SINTESI>", content, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()

            return {
                "prompt_type": prompt_name,
                "structured_data": json_data,
                "summary": summary or content,
                "raw_response": content,
                "debug_info": debug_info
            }

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return {
                "prompt_type": "error",
                "structured_data": None,
                "summary": f"Errore nell'analisi del documento: {str(e)}",
                "raw_response": "",
                "debug_info": {}
            }
