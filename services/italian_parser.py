"""
Italian Number Parser & Financial Data Normalizer

Gestisce la normalizzazione dei numeri italiani e dei dati finanziari secondo le best practices:
- Formato numeri italiani: 1.234,56 → 1234.56
- Negativi tra parentesi: (123) → -123
- Percentuali: 5% → 0.05
- Scale dichiarate: "valori in migliaia" → moltiplicatore 1000
- Provenienza tracciabile per ogni valore estratto
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Union, List, Dict, Any
from decimal import Decimal, InvalidOperation
import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ProvenancedValue:
    """Valore con provenienza tracciabile"""
    value: float
    raw_text: str
    unit: str
    currency: Optional[str] = None
    period: Optional[str] = None
    perimeter: Optional[str] = None
    source_ref: str = ""  # "file.pdf|p.12|tab:1|row:Ricavi"
    confidence: float = 1.0
    scale_factor: float = 1.0
    calculated_from: Optional[List[str]] = None
    formula: Optional[str] = None

@dataclass
class ParsedDocument:
    """Documento parsato con metadati"""
    file_path: str
    file_hash: str
    parsed_at: datetime.datetime
    detected_locale: str
    detected_currency: str
    detected_scale: float
    detected_period: Optional[str]
    values: List[ProvenancedValue]

class ItalianNumberParser:
    """Parser robusto per numeri in formato italiano"""
    
    def __init__(self):
        # Pattern per numeri italiani
        self.number_patterns = {
            # Numeri con separatori italiani
            'italian_full': r'([+-]?)(?:\()?(\d{1,3}(?:\.\d{3})*)(?:,(\d{1,4}))?(?:\))?',
            # Numeri tra parentesi (negativi)
            'parentheses': r'\((\d{1,3}(?:\.\d{3})*(?:,\d{1,4})?)\)',
            # Percentuali
            'percentage': r'([+-]?\d{1,3}(?:\.\d{3})*(?:,\d{1,4})?)\s*%',
            # Numeri con unità
            'with_unit': r'([+-]?\d{1,3}(?:\.\d{3})*(?:,\d{1,4})?)\s*(€|EUR|USD|\$|K|M|Mln|Mrd|migliaia|milioni|miliardi)',
        }
        
        # Pattern per scale dichiarate
        self.scale_patterns = {
            'migliaia': r'(?:valori?\s+in\s+)?(?:migliaia|K|000)',
            'milioni': r'(?:valori?\s+in\s+)?(?:milioni|M|Mln|000\.000)',
            'miliardi': r'(?:valori?\s+in\s+)?(?:miliardi|Mrd|B|000\.000\.000)',
        }
        
        self.scale_multipliers = {
            'migliaia': 1000,
            'milioni': 1000000,
            'miliardi': 1000000000,
            'K': 1000,
            'M': 1000000,
            'Mln': 1000000,
            'Mrd': 1000000000,
            'B': 1000000000,
        }
        
        # Sinonimi finanziari italiani
        self.financial_synonyms = {
            'ricavi': ['ricavi', 'fatturato', 'vendite', 'ricavi delle vendite', 'ricavi netti'],
            'ebitda': ['ebitda', 'mol', 'margine operativo lordo', 'risultato operativo lordo'],
            'ebit': ['ebit', 'reddito operativo', 'risultato operativo', 'margine operativo netto'],
            'pfn': ['pfn', 'posizione finanziaria netta', 'indebitamento netto', 'debito netto'],
            'patrimonio_netto': ['patrimonio netto', 'pn', 'capitale proprio', 'equity'],
            'cassa': ['cassa', 'disponibilità liquide', 'liquidità', 'cash'],
            'debito': ['debito', 'debiti finanziari', 'indebitamento', 'debito lordo'],
            'margine_lordo': ['margine lordo', 'gross margin', 'utile lordo'],
            'capex': ['capex', 'investimenti', 'immobilizzazioni', 'capital expenditure'],
        }
        
        # Pattern per periodi
        self.period_patterns = {
            'fy': r'(?:esercizio|fy|anno)\s*(\d{4})',
            'ytd': r'ytd|year\s*to\s*date|dall\'?inizio\s*anno',
            'quarter': r'(?:trimestre|q|quarter)\s*([1-4])\s*(?:del\s*)?(\d{4})',
            'month': r'(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s*(\d{4})',
        }

    def parse_number(self, text: str, source_ref: str = "") -> Optional[ProvenancedValue]:
        """
        Parsa un numero dal testo italiano
        
        Examples:
            "1.234,56" → 1234.56
            "(123,45)" → -123.45
            "5,2%" → 0.052
            "€ 1.000" → 1000.0
        """
        if not text or not isinstance(text, str):
            return None
        
        text = text.strip()
        original_text = text
        
        try:
            # Rimuovi spazi extra e caratteri non necessari
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Rileva se è una percentuale
            is_percentage = '%' in text
            
            # Rileva se è tra parentesi (negativo)
            is_negative_parentheses = text.startswith('(') and text.endswith(')')
            
            # Rileva unità/valuta
            unit = self._extract_unit(text)
            currency = self._extract_currency(text)
            scale_factor = self._extract_scale_factor(text)
            
            # Pulisci il testo per estrarre solo il numero
            clean_text = self._clean_number_text(text)
            
            if not clean_text:
                return None
            
            # Parsa il numero
            value = self._parse_clean_number(clean_text)
            if value is None:
                return None
            
            # Applica modificatori
            if is_negative_parentheses:
                value = -abs(value)
            
            if is_percentage:
                value = value / 100
                unit = '%'
            
            value *= scale_factor
            
            return ProvenancedValue(
                value=value,
                raw_text=original_text,
                unit=unit,
                currency=currency,
                source_ref=source_ref,
                scale_factor=scale_factor,
                confidence=self._calculate_confidence(original_text, value)
            )
            
        except Exception as e:
            logger.warning(f"Errore parsing numero '{original_text}': {str(e)}")
            return None

    def _clean_number_text(self, text: str) -> str:
        """Pulisce il testo mantenendo solo cifre e separatori"""
        # Rimuovi valute e unità comuni
        text = re.sub(r'[€$£¥]', '', text)
        text = re.sub(r'\b(?:EUR|USD|GBP|JPY|K|M|Mln|Mrd|migliaia|milioni|miliardi)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'%', '', text)
        
        # Rimuovi parentesi se presenti
        text = re.sub(r'[()]', '', text)
        
        # Mantieni solo cifre, punti, virgole e segni
        text = re.sub(r'[^\d+\-.,]', '', text)
        
        return text.strip()

    def _parse_clean_number(self, text: str) -> Optional[float]:
        """Parsa un numero pulito in formato italiano"""
        if not text:
            return None
        
        try:
            # Gestisci segno
            negative = text.startswith('-')
            if negative:
                text = text[1:]
            elif text.startswith('+'):
                text = text[1:]
            
            # Formato italiano: 1.234,56
            # Se c'è sia punto che virgola, punto = migliaia, virgola = decimali
            if '.' in text and ',' in text:
                # Formato: 1.234.567,89
                parts = text.split(',')
                if len(parts) == 2:
                    integer_part = parts[0].replace('.', '')
                    decimal_part = parts[1]
                    value = float(f"{integer_part}.{decimal_part}")
                else:
                    return None
            elif ',' in text:
                # Solo virgola - può essere decimale o migliaia
                if text.count(',') == 1:
                    # Probabilmente decimale: 123,45
                    parts = text.split(',')
                    if len(parts[1]) <= 2:  # Decimali tipici
                        value = float(f"{parts[0]}.{parts[1]}")
                    else:
                        # Troppi decimali, probabilmente migliaia: 1,234
                        value = float(text.replace(',', ''))
                else:
                    return None
            elif '.' in text:
                # Solo punto - può essere decimale (inglese) o migliaia (italiano)
                if text.count('.') == 1:
                    parts = text.split('.')
                    # Se ci sono 3 cifre dopo il punto, probabilmente migliaia
                    if len(parts[1]) == 3 and len(parts[0]) <= 3:
                        value = float(text.replace('.', ''))
                    else:
                        # Altrimenti decimale
                        value = float(text)
                else:
                    # Multipli punti, probabilmente migliaia: 1.234.567
                    value = float(text.replace('.', ''))
            else:
                # Solo cifre
                value = float(text)
            
            return -value if negative else value
            
        except ValueError:
            return None

    def _extract_unit(self, text: str) -> str:
        """Estrae l'unità dal testo"""
        units = ['€', 'EUR', 'USD', '$', '£', 'GBP', '%', 'K', 'M', 'Mln', 'Mrd']
        for unit in units:
            if unit in text:
                return unit
        return ''

    def _extract_currency(self, text: str) -> Optional[str]:
        """Estrae la valuta dal testo"""
        currencies = {'€': 'EUR', 'EUR': 'EUR', '$': 'USD', 'USD': 'USD', '£': 'GBP', 'GBP': 'GBP'}
        for symbol, code in currencies.items():
            if symbol in text:
                return code
        return None

    def _extract_scale_factor(self, text: str) -> float:
        """Estrae il fattore di scala dal testo"""
        text_upper = text.upper()
        for scale, multiplier in self.scale_multipliers.items():
            if scale.upper() in text_upper:
                return multiplier
        return 1.0

    def _calculate_confidence(self, original_text: str, parsed_value: float) -> float:
        """Calcola la confidenza del parsing"""
        confidence = 1.0
        
        # Riduci confidenza per testi ambigui
        if '.' in original_text and ',' in original_text:
            confidence *= 0.9  # Formato chiaro
        elif len(original_text.replace(' ', '')) < 3:
            confidence *= 0.7  # Numero molto corto
        elif not re.search(r'\d', original_text):
            confidence *= 0.0  # Nessuna cifra
        
        return max(0.0, min(1.0, confidence))

    def detect_document_metadata(self, text: str) -> Dict[str, Any]:
        """Rileva metadati del documento (locale, valuta, scala, periodo)"""
        metadata = {
            'locale': 'it_IT',
            'currency': None,
            'scale': 1.0,
            'period': None,
            'perimeter': None
        }
        
        text_lower = text.lower()
        
        # Rileva valuta prevalente
        eur_count = text.count('€') + text_lower.count('eur')
        usd_count = text.count('$') + text_lower.count('usd')
        if eur_count > usd_count:
            metadata['currency'] = 'EUR'
        elif usd_count > 0:
            metadata['currency'] = 'USD'
        
        # Rileva scala dichiarata
        for scale_name, pattern in self.scale_patterns.items():
            if re.search(pattern, text_lower):
                metadata['scale'] = self.scale_multipliers.get(scale_name, 1.0)
                break
        
        # Rileva periodo
        for period_type, pattern in self.period_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                metadata['period'] = match.group(0)
                break
        
        # Rileva perimetro
        if 'consolidat' in text_lower:
            metadata['perimeter'] = 'consolidato'
        elif 'civilistic' in text_lower:
            metadata['perimeter'] = 'civilistico'
        
        return metadata

    def normalize_metric_name(self, label: str) -> str:
        """Normalizza il nome della metrica usando sinonimi"""
        label_lower = label.lower().strip()
        
        for canonical_name, synonyms in self.financial_synonyms.items():
            for synonym in synonyms:
                if synonym in label_lower:
                    return canonical_name
        
        return label_lower

    def parse_financial_document(self, file_path: str, text: str) -> ParsedDocument:
        """Parsa un intero documento finanziario"""
        import hashlib
        
        # Calcola hash del file
        file_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Rileva metadati globali
        doc_metadata = self.detect_document_metadata(text)
        
        # Estrai tutti i numeri dal documento
        values = []
        
        # Pattern per trovare label: numero
        label_number_pattern = r'([A-Za-z][A-Za-z0-9\s\-\.]{2,50})\s*[:\-]\s*([+\-\(]?\d{1,3}(?:\.\d{3})*(?:,\d{1,4})?[%€$]?(?:\))?)'
        
        for match in re.finditer(label_number_pattern, text):
            label = match.group(1).strip()
            number_text = match.group(2).strip()
            
            # Calcola source_ref approssimativo (miglioreremo con camelot)
            line_start = text.rfind('\n', 0, match.start()) + 1
            line_num = text[:match.start()].count('\n') + 1
            source_ref = f"{Path(file_path).name}|line:{line_num}|label:{label}"
            
            parsed_value = self.parse_number(number_text, source_ref)
            if parsed_value:
                # Applica metadati documento
                parsed_value.currency = parsed_value.currency or doc_metadata['currency']
                parsed_value.period = doc_metadata['period']
                parsed_value.perimeter = doc_metadata['perimeter']
                
                # Normalizza nome metrica
                normalized_label = self.normalize_metric_name(label)
                parsed_value.source_ref += f"|metric:{normalized_label}"
                
                values.append(parsed_value)
        
        return ParsedDocument(
            file_path=file_path,
            file_hash=file_hash,
            parsed_at=datetime.datetime.now(),
            detected_locale='it_IT',
            detected_currency=doc_metadata['currency'],
            detected_scale=doc_metadata['scale'],
            detected_period=doc_metadata['period'],
            values=values
        )

class FinancialValidator:
    """Validatore per dati finanziari con controlli di coerenza"""
    
    def __init__(self):
        self.tolerance = 0.01  # 1% di tolleranza per confronti
    
    def validate_balance_sheet(self, values: List[ProvenancedValue]) -> List[str]:
        """Valida coerenza stato patrimoniale"""
        errors = []
        
        # Estrai metriche chiave
        metrics = {v.source_ref.split('|metric:')[-1]: v.value for v in values if '|metric:' in v.source_ref}
        
        # Test: Attivo = Passivo
        attivo = metrics.get('attivo_totale')
        passivo = metrics.get('passivo_totale')
        if attivo and passivo:
            if abs(attivo - passivo) / max(abs(attivo), abs(passivo)) > self.tolerance:
                errors.append(f"Squilibrio bilancio: Attivo={attivo} vs Passivo={passivo}")
        
        # Test: PFN = Debito lordo - Cassa
        pfn = metrics.get('pfn')
        debito_lordo = metrics.get('debito')
        cassa = metrics.get('cassa')
        if pfn and debito_lordo and cassa:
            expected_pfn = debito_lordo - cassa
            if abs(pfn - expected_pfn) / max(abs(pfn), abs(expected_pfn)) > self.tolerance:
                errors.append(f"Incoerenza PFN: Dichiarata={pfn} vs Calcolata={expected_pfn}")
        
        # Test: Margine lordo = Ricavi - COGS
        margine_lordo = metrics.get('margine_lordo')
        ricavi = metrics.get('ricavi')
        cogs = metrics.get('costo_del_venduto', metrics.get('cogs'))
        if margine_lordo and ricavi and cogs:
            expected_margin = ricavi - cogs
            if abs(margine_lordo - expected_margin) / max(abs(margine_lordo), abs(expected_margin)) > self.tolerance:
                errors.append(f"Incoerenza Margine Lordo: Dichiarato={margine_lordo} vs Calcolato={expected_margin}")
        
        return errors

    def validate_ranges(self, values: List[ProvenancedValue]) -> List[str]:
        """Valida range ragionevoli per le metriche"""
        errors = []
        
        for value in values:
            # Test percentuali
            if value.unit == '%':
                if value.value < -1.0 or value.value > 1.0:
                    errors.append(f"Percentuale fuori range: {value.value*100}% in {value.source_ref}")
            
            # Test valori negativi sospetti
            metric_name = value.source_ref.split('|metric:')[-1] if '|metric:' in value.source_ref else ''
            if metric_name in ['ricavi', 'cassa'] and value.value < 0:
                errors.append(f"Valore negativo sospetto per {metric_name}: {value.value}")
        
        return errors

# Esempi d'uso
if __name__ == "__main__":
    parser = ItalianNumberParser()
    validator = FinancialValidator()
    
    # Test parsing numeri
    test_cases = [
        "1.234,56",
        "(123,45)",
        "€ 1.000.000",
        "5,2%",
        "1.234.567,89",
        "valori in migliaia: 1.234"
    ]
    
    print("=== Test Parsing Numeri ===")
    for case in test_cases:
        result = parser.parse_number(case)
        print(f"Input: '{case}' → {result.value if result else 'FAILED'}")
    
    # Test documento
    print("\n=== Test Documento ===")
    sample_doc = """
    BILANCIO 2024 (valori in migliaia di Euro)
    
    Ricavi delle vendite: 5.214
    EBITDA: 547
    Cassa: 300
    Debito finanziario: 1.500
    PFN: 1.200
    """
    
    parsed_doc = parser.parse_financial_document("test.pdf", sample_doc)
    print(f"Estratti {len(parsed_doc.values)} valori")
    for value in parsed_doc.values:
        print(f"  {value.source_ref}: {value.value} {value.unit}")
    
    # Test validazioni
    errors = validator.validate_balance_sheet(parsed_doc.values)
    if errors:
        print(f"\nErrori rilevati: {errors}")
    else:
        print("\nValidazioni OK!")