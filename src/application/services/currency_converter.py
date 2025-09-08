"""Currency conversion service with real-time and historical rates."""

from forex_python.converter import CurrencyRates, CurrencyCodes
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import logging
import json
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Service for currency conversion with rate tracking."""
    
    def __init__(self, cache_dir: str = "data/currency_cache"):
        """Initialize currency converter."""
        self.rates = CurrencyRates()
        self.codes = CurrencyCodes()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Default base currency
        self.base_currency = 'EUR'
        
        # Offline fallback rates (approximate)
        self.fallback_rates = {
            'EUR': {
                'USD': 1.08,
                'GBP': 0.86,
                'JPY': 162.0,
                'CHF': 0.94,
                'CNY': 7.85,
                'CAD': 1.48,
                'AUD': 1.66,
                'SEK': 11.50,
                'NOK': 11.80,
                'DKK': 7.45
            }
        }
        
        logger.info("Currency converter initialized")
    
    def convert(self, 
                amount: float, 
                from_currency: str, 
                to_currency: str,
                date: Optional[datetime] = None,
                track_source: bool = True) -> Dict[str, Any]:
        """
        Convert amount between currencies with source tracking.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR')
            date: Date for historical rate (None for current)
            track_source: Whether to track conversion source
            
        Returns:
            Dictionary with converted amount and metadata
        """
        result = {
            'original_amount': amount,
            'original_currency': from_currency.upper(),
            'converted_amount': None,
            'converted_currency': to_currency.upper(),
            'exchange_rate': None,
            'rate_date': None,
            'source': None,
            'inverse_rate': None,
            'success': False,
            'error': None
        }
        
        # Normalize currency codes
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Same currency, no conversion needed
        if from_currency == to_currency:
            result['converted_amount'] = amount
            result['exchange_rate'] = 1.0
            result['inverse_rate'] = 1.0
            result['source'] = 'same_currency'
            result['success'] = True
            return result
        
        try:
            # Try to get rate from API
            rate, source = self._get_exchange_rate(from_currency, to_currency, date)
            
            if rate:
                result['converted_amount'] = round(amount * rate, 2)
                result['exchange_rate'] = rate
                result['inverse_rate'] = round(1 / rate, 6) if rate != 0 else None
                result['rate_date'] = date.isoformat() if date else datetime.now().isoformat()
                result['source'] = source
                result['success'] = True
                
                # Cache the rate
                if track_source:
                    self._cache_rate(from_currency, to_currency, rate, source, date)
                
            else:
                # Use fallback rates
                fallback_rate = self._get_fallback_rate(from_currency, to_currency)
                if fallback_rate:
                    result['converted_amount'] = round(amount * fallback_rate, 2)
                    result['exchange_rate'] = fallback_rate
                    result['inverse_rate'] = round(1 / fallback_rate, 6)
                    result['source'] = 'fallback'
                    result['success'] = True
                    result['error'] = 'Using fallback rates (API unavailable)'
                else:
                    result['error'] = f'No rate available for {from_currency}/{to_currency}'
                    
        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            result['error'] = str(e)
            
            # Try fallback
            try:
                fallback_rate = self._get_fallback_rate(from_currency, to_currency)
                if fallback_rate:
                    result['converted_amount'] = round(amount * fallback_rate, 2)
                    result['exchange_rate'] = fallback_rate
                    result['source'] = 'fallback'
                    result['success'] = True
                    result['error'] = f'API error, using fallback: {e}'
            except:
                pass
        
        return result
    
    def _get_exchange_rate(self, 
                          from_currency: str, 
                          to_currency: str,
                          date: Optional[datetime] = None) -> Tuple[Optional[float], str]:
        """Get exchange rate from API or cache."""
        
        # Check cache first
        cached_rate = self._get_cached_rate(from_currency, to_currency, date)
        if cached_rate:
            return cached_rate, 'cache'
        
        try:
            if date and date < datetime.now() - timedelta(days=1):
                # Historical rate
                rate = self.rates.get_rate(from_currency, to_currency, date)
                return rate, 'forex_api_historical'
            else:
                # Current rate
                rate = self.rates.get_rate(from_currency, to_currency)
                return rate, 'forex_api_current'
        except Exception as e:
            logger.warning(f"API rate fetch failed: {e}")
            return None, None
    
    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """Get fallback exchange rate."""
        
        # Direct rate
        if from_currency in self.fallback_rates:
            if to_currency in self.fallback_rates[from_currency]:
                return self.fallback_rates[from_currency][to_currency]
        
        # Inverse rate
        if to_currency in self.fallback_rates:
            if from_currency in self.fallback_rates[to_currency]:
                return 1 / self.fallback_rates[to_currency][from_currency]
        
        # Cross rate through EUR
        if from_currency != 'EUR' and to_currency != 'EUR':
            if from_currency in self.fallback_rates['EUR'] and to_currency in self.fallback_rates['EUR']:
                from_eur_rate = self.fallback_rates['EUR'][from_currency]
                to_eur_rate = self.fallback_rates['EUR'][to_currency]
                return to_eur_rate / from_eur_rate
        
        return None
    
    def _cache_rate(self, 
                   from_currency: str, 
                   to_currency: str, 
                   rate: float, 
                   source: str,
                   date: Optional[datetime] = None):
        """Cache exchange rate."""
        cache_key = f"{from_currency}_{to_currency}"
        if date:
            cache_key += f"_{date.strftime('%Y%m%d')}"
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
            'source': source,
            'cached_at': datetime.now().isoformat(),
            'rate_date': date.isoformat() if date else datetime.now().isoformat()
        }
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to cache rate: {e}")
    
    def _get_cached_rate(self, 
                        from_currency: str, 
                        to_currency: str,
                        date: Optional[datetime] = None) -> Optional[float]:
        """Get cached exchange rate."""
        cache_key = f"{from_currency}_{to_currency}"
        if date:
            cache_key += f"_{date.strftime('%Y%m%d')}"
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if cache is recent (within 24 hours for current rates)
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                if not date:  # Current rate
                    if datetime.now() - cached_time < timedelta(hours=24):
                        return cache_data['rate']
                else:  # Historical rate (can use older cache)
                    return cache_data['rate']
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")
        
        return None
    
    def get_currency_symbol(self, currency_code: str) -> str:
        """Get currency symbol."""
        try:
            return self.codes.get_symbol(currency_code.upper())
        except:
            # Fallback symbols
            symbols = {
                'EUR': '€',
                'USD': '$',
                'GBP': '£',
                'JPY': '¥',
                'CNY': '¥',
                'CHF': 'CHF',
                'CAD': 'C$',
                'AUD': 'A$'
            }
            return symbols.get(currency_code.upper(), currency_code)
    
    def get_currency_name(self, currency_code: str) -> str:
        """Get currency full name."""
        try:
            return self.codes.get_currency_name(currency_code.upper())
        except:
            # Fallback names
            names = {
                'EUR': 'Euro',
                'USD': 'US Dollar',
                'GBP': 'British Pound',
                'JPY': 'Japanese Yen',
                'CNY': 'Chinese Yuan',
                'CHF': 'Swiss Franc',
                'CAD': 'Canadian Dollar',
                'AUD': 'Australian Dollar'
            }
            return names.get(currency_code.upper(), currency_code)
    
    @lru_cache(maxsize=100)
    def get_available_currencies(self) -> Dict[str, str]:
        """Get list of available currencies."""
        try:
            # Get from API
            currencies = self.rates.get_rates('USD')
            available = {'USD': 'US Dollar'}
            
            for code in currencies.keys():
                try:
                    name = self.get_currency_name(code)
                    available[code] = name
                except:
                    available[code] = code
            
            return available
        except:
            # Return common currencies
            return {
                'EUR': 'Euro',
                'USD': 'US Dollar',
                'GBP': 'British Pound',
                'JPY': 'Japanese Yen',
                'CHF': 'Swiss Franc',
                'CAD': 'Canadian Dollar',
                'AUD': 'Australian Dollar',
                'CNY': 'Chinese Yuan'
            }
    
    def convert_financial_data(self, 
                              data: Dict[str, Any], 
                              target_currency: str,
                              date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Convert all monetary values in financial data to target currency.
        
        Args:
            data: Financial data dictionary
            target_currency: Target currency code
            date: Date for historical rates
            
        Returns:
            Converted data with conversion metadata
        """
        converted = {
            'original_data': data.copy(),
            'converted_data': {},
            'target_currency': target_currency,
            'conversions': []
        }
        
        # Fields that typically contain monetary values
        monetary_fields = [
            'ricavi', 'revenue', 'sales', 'fatturato',
            'ebitda', 'ebit', 'mol',
            'utile_netto', 'net_income', 'profit',
            'cassa', 'cash', 'debito', 'debt',
            'attivo', 'assets', 'passivo', 'liabilities',
            'patrimonio_netto', 'equity'
        ]
        
        for key, value in data.items():
            # Check if field might be monetary
            is_monetary = any(field in key.lower() for field in monetary_fields)
            
            if is_monetary and isinstance(value, dict):
                # Value with currency info
                if 'value' in value and 'currency' in value:
                    conversion = self.convert(
                        value['value'],
                        value['currency'],
                        target_currency,
                        date
                    )
                    converted['converted_data'][key] = {
                        'value': conversion['converted_amount'],
                        'currency': target_currency,
                        'original': value,
                        'rate': conversion['exchange_rate']
                    }
                    converted['conversions'].append({
                        'field': key,
                        **conversion
                    })
                else:
                    converted['converted_data'][key] = value
            elif is_monetary and isinstance(value, (int, float)):
                # Assume EUR if no currency specified
                conversion = self.convert(
                    value,
                    'EUR',
                    target_currency,
                    date
                )
                converted['converted_data'][key] = conversion['converted_amount']
                converted['conversions'].append({
                    'field': key,
                    **conversion
                })
            else:
                # Non-monetary field
                converted['converted_data'][key] = value
        
        return converted
    
    def format_currency(self, 
                       amount: float, 
                       currency_code: str,
                       include_symbol: bool = True) -> str:
        """Format amount as currency string."""
        symbol = self.get_currency_symbol(currency_code) if include_symbol else ''
        
        # Format with thousands separator
        formatted = f"{amount:,.2f}"
        
        # Apply currency-specific formatting
        if currency_code == 'EUR':
            # European style: 1.234,56 €
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"{formatted} {symbol}" if include_symbol else formatted
        else:
            # US/UK style: $1,234.56
            return f"{symbol}{formatted}" if include_symbol else formatted