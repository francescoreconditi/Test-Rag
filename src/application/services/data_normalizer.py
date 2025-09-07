"""Data normalization service for financial data."""

import re
import locale
import json
import requests
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, Tuple, Union, List
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
try:
    import babel.numbers
    from babel.core import Locale
    BABEL_AVAILABLE = True
except ImportError:
    BABEL_AVAILABLE = False
import dateutil.parser
import logging

logger = logging.getLogger(__name__)


class ScaleUnit(Enum):
    """Scale units for financial data."""
    UNITS = ("units", 1)
    THOUSANDS = ("thousands", 1_000)
    MILLIONS = ("millions", 1_000_000) 
    BILLIONS = ("billions", 1_000_000_000)
    
    def __init__(self, name: str, multiplier: int):
        self.unit_name = name
        self.multiplier = multiplier


class PeriodType(Enum):
    """Types of financial periods."""
    YEAR = "FY"       # Full year
    QUARTER = "Q"     # Quarter
    MONTH = "M"       # Month
    YTD = "YTD"       # Year to date
    CUSTOM = "CUSTOM" # Custom date range


@dataclass
class NormalizedPeriod:
    """Normalized period representation."""
    period_type: PeriodType
    year: int
    period_number: Optional[int] = None  # Quarter (1-4) or Month (1-12)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    display_name: str = ""
    
    def __post_init__(self):
        """Generate display name if not provided."""
        if not self.display_name:
            if self.period_type == PeriodType.YEAR:
                self.display_name = f"FY{self.year}"
            elif self.period_type == PeriodType.QUARTER:
                self.display_name = f"Q{self.period_number} {self.year}"
            elif self.period_type == PeriodType.MONTH:
                self.display_name = f"M{self.period_number:02d} {self.year}"
            elif self.period_type == PeriodType.YTD:
                self.display_name = f"YTD {self.year}"
            else:
                self.display_name = f"{self.start_date} to {self.end_date}"


@dataclass
class CurrencyRate:
    """Currency conversion rate with metadata."""
    from_currency: str
    to_currency: str
    rate: Decimal
    source: str
    timestamp: datetime
    
    
@dataclass 
class NormalizedValue:
    """A normalized numeric value with metadata."""
    value: Decimal
    original_value: str
    scale_applied: ScaleUnit
    currency: Optional[str] = None
    is_negative: bool = False
    is_percentage: bool = False
    confidence: float = 1.0
    conversion_rate: Optional[CurrencyRate] = None
    
    def to_float(self) -> float:
        """Convert to float for calculations."""
        return float(self.value)
    
    def to_base_units(self) -> float:
        """Convert to base units (applying scale)."""
        base_value = float(self.value * self.scale_applied.multiplier)
        if self.is_percentage:
            return base_value / 100.0
        return base_value
    
    def convert_currency(self, target_currency: str, rate: CurrencyRate) -> 'NormalizedValue':
        """Convert to different currency."""
        if not self.currency or self.currency == target_currency:
            return self
        
        converted_value = self.value * rate.rate
        
        return NormalizedValue(
            value=converted_value,
            original_value=self.original_value,
            scale_applied=self.scale_applied,
            currency=target_currency,
            is_negative=self.is_negative,
            is_percentage=self.is_percentage,
            confidence=self.confidence * 0.95,  # Slight confidence reduction for conversion
            conversion_rate=rate
        )


class DataNormalizer:
    """Service for normalizing financial data."""
    
    def __init__(self, default_locale: str = "it_IT", enable_currency_conversion: bool = False):
        """Initialize normalizer with locale settings."""
        self.default_locale = default_locale
        self.enable_currency_conversion = enable_currency_conversion
        self.currency_rates_cache: Dict[str, CurrencyRate] = {}
        self.rates_cache_file = Path("cache/currency_rates.json")
        self.rates_cache_file.parent.mkdir(exist_ok=True)
        
        if BABEL_AVAILABLE:
            try:
                self.babel_locale = Locale.parse(default_locale)
            except:
                self.babel_locale = Locale.parse("en_US")
        else:
            self.babel_locale = None
            
        # Load cached rates
        self._load_cached_rates()
        
        # Common scale indicators
        self.scale_patterns = {
            ScaleUnit.THOUSANDS: [
                r'(?i)valori\s+in\s+migliaia',
                r'(?i)in\s+thousands?',
                r'(?i)\(000\)',
                r'(?i)k€', r'(?i)k\$',
                r'(?i)migliaia\s+di\s+euro'
            ],
            ScaleUnit.MILLIONS: [
                r'(?i)valori\s+in\s+milioni',
                r'(?i)in\s+millions?',
                r'(?i)\(000,000\)',
                r'(?i)m€', r'(?i)m\$',
                r'(?i)milioni\s+di\s+euro'
            ],
            ScaleUnit.BILLIONS: [
                r'(?i)valori\s+in\s+miliardi',
                r'(?i)in\s+billions?',
                r'(?i)b€', r'(?i)b\$',
                r'(?i)miliardi\s+di\s+euro'
            ]
        }
        
        # Currency patterns
        self.currency_patterns = [
            (r'€|EUR|euro', 'EUR'),
            (r'\$|USD|dollar', 'USD'),
            (r'£|GBP|pound', 'GBP'),
            (r'¥|JPY|yen', 'JPY')
        ]
        
        # Percentage patterns
        self.percentage_patterns = [
            r'%',
            r'(?i)percentuale',
            r'(?i)percent',
            r'(?i)per\s+cent'
        ]
        
        # Period patterns
        self.period_patterns = {
            'year': [
                r'(?i)esercizio\s+(\d{4})',
                r'(?i)anno\s+(\d{4})',
                r'(?i)fy\s*(\d{4})',
                r'(?i)year\s+(\d{4})',
                r'(\d{4})$'
            ],
            'quarter': [
                r'(?i)q([1-4])\s+(\d{4})',
                r'(?i)trimestre\s+([1-4])\s+(\d{4})',
                r'(?i)(\d{4})\s*q([1-4])'
            ],
            'ytd': [
                r'(?i)ytd\s+(\d{4})',
                r'(?i)(\d{4})\s+ytd'
            ]
        }
    
    def detect_scale(self, text: str) -> ScaleUnit:
        """Detect scale from text context."""
        text_lower = text.lower()
        
        for scale_unit, patterns in self.scale_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return scale_unit
        
        return ScaleUnit.UNITS
    
    def normalize_number(self, 
                        value_str: str, 
                        context: str = "",
                        detected_scale: Optional[ScaleUnit] = None) -> Optional[NormalizedValue]:
        """Normalize a numeric string to standard format."""
        if not value_str or str(value_str).strip() == "":
            return None
        
        original_value = str(value_str).strip()
        
        # Detect currency and percentage
        currency = self._extract_currency(original_value)
        is_percentage = self._is_percentage(original_value + " " + context)
        
        # Clean the string
        clean_value = self._clean_numeric_string(original_value)
        if not clean_value:
            return None
        
        # Check for negative (parentheses or minus)
        is_negative = False
        if clean_value.startswith('(') and clean_value.endswith(')'):
            clean_value = clean_value[1:-1]
            is_negative = True
        elif clean_value.startswith('-'):
            clean_value = clean_value[1:]
            is_negative = True
        
        # Parse number based on locale
        try:
            # Try Italian format first (1.234,56)
            if ',' in clean_value and '.' in clean_value:
                # Both comma and dot - check which is decimal separator
                last_comma = clean_value.rfind(',')
                last_dot = clean_value.rfind('.')
                
                if last_comma > last_dot:
                    # Italian: 1.234.567,89
                    clean_value = clean_value.replace('.', '').replace(',', '.')
                else:
                    # US: 1,234,567.89  
                    clean_value = clean_value.replace(',', '')
            elif ',' in clean_value:
                # Only comma - could be decimal (Italian) or thousands (US)
                parts = clean_value.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Likely decimal: 1234,56
                    clean_value = clean_value.replace(',', '.')
                else:
                    # Likely thousands: 1,234,567
                    clean_value = clean_value.replace(',', '')
            
            decimal_value = Decimal(clean_value)
            
            if is_negative:
                decimal_value = -decimal_value
            
            # Apply scale
            scale = detected_scale or self.detect_scale(context)
            
            return NormalizedValue(
                value=decimal_value,
                original_value=original_value,
                scale_applied=scale,
                currency=currency,
                is_negative=is_negative,
                is_percentage=is_percentage,
                confidence=self._calculate_confidence(original_value, clean_value)
            )
            
        except (InvalidOperation, ValueError, TypeError) as e:
            return None
    
    def _clean_numeric_string(self, value_str: str) -> str:
        """Clean numeric string removing non-numeric chars except separators."""
        if not value_str:
            return ""
        
        # Remove currency symbols and extra whitespace
        clean = re.sub(r'[€$£¥₹]|EUR|USD|GBP|JPY', '', value_str)
        clean = re.sub(r'\s+', '', clean)  # Remove all whitespace
        
        # Keep only digits, commas, dots, parentheses, and minus
        clean = re.sub(r'[^\d,.\-()]', '', clean)
        
        return clean.strip()
    
    def _extract_currency(self, value_str: str) -> Optional[str]:
        """Extract currency code from value string."""
        for pattern, currency_code in self.currency_patterns:
            if re.search(pattern, value_str):
                return currency_code
        return None
    
    def _calculate_confidence(self, original: str, cleaned: str) -> float:
        """Calculate confidence score for number parsing."""
        if not original or not cleaned:
            return 0.0
        
        # Higher confidence if the cleaning didn't change much
        similarity = len(cleaned) / len(original) if len(original) > 0 else 0
        
        # Boost confidence for common patterns
        confidence = 0.7  # Base confidence
        
        if re.search(r'^\d{1,3}([\.,]\d{3})*[\.,]?\d{0,2}$', cleaned):
            confidence += 0.2  # Well-formed number
        
        if '€' in original or 'EUR' in original:
            confidence += 0.1  # Clear currency indicator
        
        return min(1.0, confidence)
    
    def normalize_period(self, period_str: str) -> Optional[NormalizedPeriod]:
        """Normalize period string to standard format."""
        if not period_str:
            return None
        
        period_clean = period_str.strip()
        
        # Try year patterns
        for pattern in self.period_patterns['year']:
            match = re.search(pattern, period_clean)
            if match:
                year = int(match.group(1))
                return NormalizedPeriod(
                    period_type=PeriodType.YEAR,
                    year=year,
                    start_date=date(year, 1, 1),
                    end_date=date(year, 12, 31)
                )
        
        # Try quarter patterns  
        for pattern in self.period_patterns['quarter']:
            match = re.search(pattern, period_clean)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    quarter = int(groups[0])
                    year = int(groups[1])
                else:
                    # Handle reversed pattern
                    year = int(groups[0])
                    quarter = int(groups[1])
                
                # Calculate quarter dates
                start_month = (quarter - 1) * 3 + 1
                if quarter < 4:
                    end_month = quarter * 3
                    end_year = year
                else:
                    end_month = 12
                    end_year = year
                
                return NormalizedPeriod(
                    period_type=PeriodType.QUARTER,
                    year=year,
                    period_number=quarter,
                    start_date=date(year, start_month, 1),
                    end_date=self._last_day_of_month(end_year, end_month)
                )
        
        # Try YTD patterns
        for pattern in self.period_patterns['ytd']:
            match = re.search(pattern, period_clean)
            if match:
                year = int(match.group(1))
                return NormalizedPeriod(
                    period_type=PeriodType.YTD,
                    year=year,
                    start_date=date(year, 1, 1),
                    end_date=date.today() if year == date.today().year else date(year, 12, 31)
                )
        
        # Try to parse as date range
        if '–' in period_clean or '-' in period_clean or 'to' in period_clean.lower():
            return self._parse_date_range(period_clean)
        
        return None
    
    def _last_day_of_month(self, year: int, month: int) -> date:
        """Get last day of month."""
        import datetime
        if month == 12:
            return date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            return date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    def _parse_date_range(self, range_str: str) -> Optional[NormalizedPeriod]:
        """Parse date range string."""
        try:
            # Split on common separators
            separators = ['–', '-', ' to ', ' - ']
            parts = None
            
            for sep in separators:
                if sep in range_str:
                    parts = range_str.split(sep, 1)
                    break
            
            if not parts or len(parts) != 2:
                return None
            
            start_str, end_str = [p.strip() for p in parts]
            
            # Parse dates
            start_date = dateutil.parser.parse(start_str, dayfirst=True).date()
            end_date = dateutil.parser.parse(end_str, dayfirst=True).date()
            
            # Determine period type
            days_diff = (end_date - start_date).days
            
            if days_diff <= 35:  # Monthly
                period_type = PeriodType.MONTH
                period_number = start_date.month
            elif days_diff <= 100:  # Quarterly
                period_type = PeriodType.QUARTER
                period_number = (start_date.month - 1) // 3 + 1
            elif days_diff >= 360:  # Yearly
                period_type = PeriodType.YEAR
                period_number = None
            else:
                period_type = PeriodType.CUSTOM
                period_number = None
            
            return NormalizedPeriod(
                period_type=period_type,
                year=start_date.year,
                period_number=period_number,
                start_date=start_date,
                end_date=end_date
            )
            
        except (ValueError, OverflowError) as e:
            return None
    
    def batch_normalize(self, 
                       data: Dict[str, Any], 
                       context: str = "",
                       scale_override: Optional[ScaleUnit] = None) -> Dict[str, NormalizedValue]:
        """Batch normalize multiple values."""
        results = {}
        detected_scale = scale_override or self.detect_scale(context)
        
        for key, value in data.items():
            if isinstance(value, (str, int, float)):
                normalized = self.normalize_number(str(value), context, detected_scale)
                if normalized:
                    results[key] = normalized
        
        return results
    
    def _is_percentage(self, text: str) -> bool:
        """Check if value represents a percentage."""
        for pattern in self.percentage_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _load_cached_rates(self):
        """Load cached currency rates."""
        try:
            if self.rates_cache_file.exists():
                with open(self.rates_cache_file, 'r') as f:
                    data = json.load(f)
                    for key, rate_data in data.items():
                        rate = CurrencyRate(
                            from_currency=rate_data['from_currency'],
                            to_currency=rate_data['to_currency'],
                            rate=Decimal(str(rate_data['rate'])),
                            source=rate_data['source'],
                            timestamp=datetime.fromisoformat(rate_data['timestamp'])
                        )
                        self.currency_rates_cache[key] = rate
        except Exception as e:
            logger.warning(f"Failed to load currency rates cache: {e}")
    
    def _save_cached_rates(self):
        """Save currency rates to cache."""
        try:
            data = {}
            for key, rate in self.currency_rates_cache.items():
                data[key] = {
                    'from_currency': rate.from_currency,
                    'to_currency': rate.to_currency,
                    'rate': str(rate.rate),
                    'source': rate.source,
                    'timestamp': rate.timestamp.isoformat()
                }
            
            with open(self.rates_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save currency rates cache: {e}")
    
    def get_currency_rate(self, from_currency: str, to_currency: str) -> Optional[CurrencyRate]:
        """Get currency exchange rate."""
        if from_currency == to_currency:
            return CurrencyRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=Decimal('1.0'),
                source='identity',
                timestamp=datetime.now()
            )
        
        cache_key = f"{from_currency}_{to_currency}"
        
        # Check cache first (rates valid for 1 hour)
        if cache_key in self.currency_rates_cache:
            cached_rate = self.currency_rates_cache[cache_key]
            if (datetime.now() - cached_rate.timestamp).seconds < 3600:
                return cached_rate
        
        # Try to fetch from external API (example with exchangerate-api.com)
        if self.enable_currency_conversion:
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                if to_currency in data['rates']:
                    rate = CurrencyRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=Decimal(str(data['rates'][to_currency])),
                        source='exchangerate-api.com',
                        timestamp=datetime.now()
                    )
                    
                    # Cache the rate
                    self.currency_rates_cache[cache_key] = rate
                    self._save_cached_rates()
                    
                    return rate
                    
            except Exception as e:
                logger.warning(f"Failed to fetch currency rate {from_currency}->{to_currency}: {e}")
        
        return None
    
    def convert_currency(self, value: NormalizedValue, target_currency: str) -> Optional[NormalizedValue]:
        """Convert normalized value to target currency."""
        if not value.currency or value.currency == target_currency:
            return value
        
        rate = self.get_currency_rate(value.currency, target_currency)
        if rate:
            return value.convert_currency(target_currency, rate)
        
        return None
    
    def get_normalization_summary(self, results: Dict[str, NormalizedValue]) -> Dict[str, Any]:
        """Get summary of normalization results."""
        if not results:
            return {'total': 0, 'success_rate': 0}
        
        total = len(results)
        avg_confidence = sum(r.confidence for r in results.values()) / total
        currencies = set(r.currency for r in results.values() if r.currency)
        scales = set(r.scale_applied for r in results.values())
        
        return {
            'total': total,
            'success_rate': 100.0,  # All results are successful by definition
            'average_confidence': avg_confidence,
            'currencies_found': list(currencies),
            'scales_detected': [s.unit_name for s in scales],
            'negative_values': sum(1 for r in results.values() if r.is_negative),
            'percentage_values': sum(1 for r in results.values() if r.is_percentage)
        }