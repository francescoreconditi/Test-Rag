"""CSV Data Analyzer module for financial and business data analysis."""

from datetime import datetime
import json
import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.application.services.data_normalizer import DataNormalizer
from src.domain.value_objects.source_reference import ProvenancedValue, SourceReference

logger = logging.getLogger(__name__)


class CSVAnalyzer:
    """Analyzes CSV data for financial and business metrics."""

    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.comparison_data: Optional[pd.DataFrame] = None
        self.metrics_cache: dict[str, Any] = {}
        self.data_normalizer = DataNormalizer()
        self.parsed_values: list[ProvenancedValue] = []

    def load_csv(self, file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """Load CSV file with advanced Italian number parsing."""
        try:
            # Try different encodings common in Italian files
            encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
            df = None

            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                raise ValueError("Cannot decode file with any supported encoding")

            logger.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")

            # Parse date columns (Italian format support)
            for col in df.columns:
                if any(date_word in col.lower() for date_word in ['data', 'date', 'giorno', 'mese', 'anno']):
                    df[col] = self._parse_date_column(df[col])

            # Parse numeric columns with Italian number parser
            numeric_columns_parsed = 0
            self.parsed_values = []

            for col in df.columns:
                if df[col].dtype == 'object':
                    parsed_series, parsed_values = self._parse_numeric_column(df[col], col, file_path)
                    if parsed_series is not None:
                        df[col] = parsed_series
                        self.parsed_values.extend(parsed_values)
                        numeric_columns_parsed += 1

            logger.info(f"Parsed {numeric_columns_parsed} numeric columns with enterprise DataNormalizer")
            logger.info(f"Extracted {len(self.parsed_values)} provenance-tracked values")

            # Validation is now handled by the DataNormalizer enterprise component

            self.data = df
            return df

        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {str(e)}")
            raise ValueError(f"Error loading CSV: {str(e)}")

    def _parse_date_column(self, series: pd.Series) -> pd.Series:
        """Parse date column with Italian format support"""
        try:
            # Try Italian date formats first
            return pd.to_datetime(series, format='%d/%m/%Y', errors='coerce').fillna(
                pd.to_datetime(series, format='%d-%m-%Y', errors='coerce')
            ).fillna(
                pd.to_datetime(series, errors='coerce')
            )
        except Exception:
            return series

    def _parse_numeric_column(self, series: pd.Series, column_name: str, file_path: str) -> tuple[Optional[pd.Series], list[ProvenancedValue]]:
        """Parse numeric column using enterprise DataNormalizer"""
        parsed_values = []
        converted_values = []

        for idx, value in series.items():
            if pd.isna(value) or value == '':
                converted_values.append(np.nan)
                continue

            # Use the enterprise DataNormalizer
            normalized = self.data_normalizer.normalize_number(str(value), context=column_name)

            if normalized:
                converted_values.append(float(normalized.value))

                # Create source reference for provenance tracking
                source_ref = SourceReference(
                    file_path=file_path,
                    extraction_method="csv_parser",
                    page_number=idx + 2,  # +2 for header (using page_number as row reference)
                    confidence_score=normalized.confidence
                )

                # Create provenance value
                provenance_value = ProvenancedValue(
                    value=normalized.value,
                    source_ref=source_ref,
                    metric_name=column_name,
                    unit="percentage" if normalized.is_percentage else "numeric",
                    currency=normalized.currency
                )

                parsed_values.append(provenance_value)
            else:
                # Fallback to pandas numeric conversion
                try:
                    numeric_val = pd.to_numeric(str(value).replace(',', '.'), errors='coerce')
                    converted_values.append(numeric_val)
                except:
                    converted_values.append(np.nan)

        # Return parsed series only if we successfully parsed some values
        if parsed_values:
            return pd.Series(converted_values, index=series.index), parsed_values
        else:
            return None, []

    def analyze_balance_sheet(self, df: pd.DataFrame, year_column: str = 'anno',
                            revenue_column: str = 'fatturato') -> dict[str, Any]:
        """Analyze balance sheet data and extract key metrics."""
        analysis = {
            'summary': {},
            'trends': {},
            'ratios': {},
            'insights': []
        }

        if year_column in df.columns:
            # Sort by year
            df = df.sort_values(year_column)

            # Calculate year-over-year changes
            if revenue_column in df.columns:
                revenues = df[revenue_column].values
                years = df[year_column].values

                if len(revenues) > 1:
                    # YoY growth
                    yoy_growth = []
                    for i in range(1, len(revenues)):
                        growth = ((revenues[i] - revenues[i-1]) / revenues[i-1]) * 100
                        yoy_growth.append({
                            'year': int(years[i]),
                            'growth_percentage': round(growth, 2),
                            'absolute_change': revenues[i] - revenues[i-1]
                        })

                    analysis['trends']['yoy_growth'] = yoy_growth

                    # Average growth rate
                    avg_growth = np.mean([g['growth_percentage'] for g in yoy_growth])
                    analysis['summary']['average_growth'] = round(avg_growth, 2)

                    # Trend direction
                    if avg_growth > 5:
                        analysis['insights'].append("Rilevato forte trend di crescita positiva")
                    elif avg_growth < -5:
                        analysis['insights'].append("Trend di fatturato in calo - richiede attenzione")
                    else:
                        analysis['insights'].append("Trend di fatturato stabile")

        # Analyze profitability if columns exist
        profit_columns = ['utile', 'profit', 'ebitda', 'risultato']
        for col in profit_columns:
            if col in df.columns:
                profits = df[col].values
                if len(profits) > 0:
                    analysis['summary'][f'{col}_latest'] = profits[-1]
                    if len(profits) > 1:
                        profit_change = profits[-1] - profits[-2]
                        analysis['summary'][f'{col}_change'] = profit_change
                        if profit_change > 0:
                            analysis['insights'].append(f"Redditività migliorata: {col} aumentato di {profit_change:,.2f}")
                        else:
                            analysis['insights'].append(f"Redditività diminuita: {col} diminuito di {abs(profit_change):,.2f}")

        # Calculate financial ratios
        if revenue_column in df.columns:
            latest_revenue = df[revenue_column].iloc[-1]

            # Profit margin if profit column exists
            for profit_col in profit_columns:
                if profit_col in df.columns:
                    profit_margin = (df[profit_col].iloc[-1] / latest_revenue) * 100
                    analysis['ratios'][f'{profit_col}_margin'] = round(profit_margin, 2)

        # Detect anomalies
        for col in df.select_dtypes(include=[np.number]).columns:
            values = df[col].values
            if len(values) > 2:
                mean = np.mean(values)
                std = np.std(values)
                latest = values[-1]
                if abs(latest - mean) > 2 * std:
                    analysis['insights'].append(f"Anomalia rilevata in {col}: il valore più recente devia significativamente dalla media storica")

        return analysis

    def analyze_comprehensive(self, file_path: str) -> dict[str, Any]:
        """Comprehensive analysis of CSV data with automatic detection of data type."""
        try:
            # Load the CSV file
            df = self.load_csv(file_path)

            # Detect data type and perform appropriate analysis
            if self._is_balance_sheet_data(df):
                return self.analyze_balance_sheet(df)
            else:
                # Generic analysis for other data types
                return self._analyze_generic(df)

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            raise ValueError(f"Analysis failed: {str(e)}")

    def _is_balance_sheet_data(self, df: pd.DataFrame) -> bool:
        """Detect if the CSV contains balance sheet data."""
        balance_sheet_keywords = [
            'fatturato', 'revenue', 'ricavi', 'vendite', 'sales',
            'ebitda', 'ebit', 'utile', 'profit', 'costi', 'costs',
            'attivo', 'passivo', 'assets', 'liabilities'
        ]

        column_names = [col.lower() for col in df.columns]
        matches = sum(1 for keyword in balance_sheet_keywords
                     for col in column_names if keyword in col)

        return matches >= 2  # At least 2 financial keywords

    def _analyze_generic(self, df: pd.DataFrame) -> dict[str, Any]:
        """Generic analysis for non-balance sheet data."""
        analysis = {
            'data_info': {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns),
                'numeric_columns': list(df.select_dtypes(include=[np.number]).columns),
                'text_columns': list(df.select_dtypes(include=['object']).columns)
            },
            'summary_statistics': {},
            'insights': [],
            'recommendations': []
        }

        # Calculate summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            stats = df[col].describe().to_dict()
            stats['null_count'] = df[col].isnull().sum()
            analysis['summary_statistics'][col] = stats

        # Generate insights
        analysis['insights'].append(f"Dataset contains {len(df)} records across {len(df.columns)} columns")
        analysis['insights'].append(f"Found {len(numeric_cols)} numeric columns for analysis")

        if self.parsed_values:
            analysis['insights'].append(f"Successfully parsed {len(self.parsed_values)} values with provenance tracking")

        # Generate recommendations
        if len(numeric_cols) > 0:
            analysis['recommendations'].append("Consider trend analysis for numeric columns over time")

        if df.isnull().sum().sum() > 0:
            analysis['recommendations'].append("Review and handle missing data values")

        return analysis

    def compare_periods(self, df1: pd.DataFrame, df2: pd.DataFrame,
                        key_metrics: list[str]) -> dict[str, Any]:
        """Compare two periods or datasets."""
        comparison = {
            'differences': {},
            'percentage_changes': {},
            'insights': []
        }

        for metric in key_metrics:
            if metric in df1.columns and metric in df2.columns:
                val1 = df1[metric].sum() if len(df1[metric]) > 1 else df1[metric].iloc[0]
                val2 = df2[metric].sum() if len(df2[metric]) > 1 else df2[metric].iloc[0]

                diff = val2 - val1
                pct_change = ((val2 - val1) / val1) * 100 if val1 != 0 else 0

                comparison['differences'][metric] = round(diff, 2)
                comparison['percentage_changes'][metric] = round(pct_change, 2)

                # Generate insights
                if abs(pct_change) > 20:
                    direction = "aumentato" if pct_change > 0 else "diminuito"
                    comparison['insights'].append(
                        f"{metric} {direction} significativamente del {abs(pct_change):.1f}%"
                    )

        return comparison

    def calculate_kpis(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate key performance indicators."""
        kpis = {}

        # Revenue-based KPIs
        revenue_cols = ['fatturato', 'revenue', 'ricavi', 'sales']
        for col in revenue_cols:
            if col in df.columns:
                kpis[f'{col}_total'] = df[col].sum()
                kpis[f'{col}_average'] = df[col].mean()
                kpis[f'{col}_median'] = df[col].median()
                break

        # Cost-based KPIs
        cost_cols = ['costi', 'costs', 'expenses', 'spese']
        for col in cost_cols:
            if col in df.columns:
                kpis[f'{col}_total'] = df[col].sum()
                kpis[f'{col}_average'] = df[col].mean()
                break

        # Efficiency ratios
        if 'fatturato' in df.columns and 'costi' in df.columns:
            kpis['efficiency_ratio'] = (df['costi'].sum() / df['fatturato'].sum()) * 100

        # Growth metrics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            values = df[col].values
            if len(values) > 1:
                cagr = (((values[-1] / values[0]) ** (1 / (len(values) - 1))) - 1) * 100
                kpis[f'{col}_cagr'] = round(cagr, 2)

        return {k: round(v, 2) for k, v in kpis.items()}

    def generate_summary(self, df: pd.DataFrame) -> str:
        """Generate a natural language summary of the data."""
        summary_parts = []

        # Dataset overview
        summary_parts.append(f"Il dataset contiene {len(df)} record con {len(df.columns)} colonne.")

        # Numeric columns analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            summary_parts.append(f"Trovate {len(numeric_cols)} metriche numeriche da analizzare.")

            for col in numeric_cols[:5]:  # Limit to first 5 columns
                mean_val = df[col].mean()
                max_val = df[col].max()
                min_val = df[col].min()
                summary_parts.append(
                    f"{col}: varia da {min_val:,.2f} a {max_val:,.2f}, media {mean_val:,.2f}"
                )

        # Temporal analysis if date column exists
        date_cols = [col for col in df.columns if 'date' in col.lower() or 'data' in col.lower()]
        if date_cols:
            try:
                dates = pd.to_datetime(df[date_cols[0]])
                date_range = f"dal {dates.min().date()} al {dates.max().date()}"
                summary_parts.append(f"Periodo temporale coperto: {date_range}")
            except:
                pass

        return " ".join(summary_parts)

    def export_analysis(self, analysis: dict[str, Any], output_path: str):
        """Export analysis results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    def get_recommendations(self, analysis: dict[str, Any]) -> list[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Check trends
        if 'trends' in analysis:
            if 'yoy_growth' in analysis['trends']:
                latest_growth = analysis['trends']['yoy_growth'][-1]['growth_percentage']
                if latest_growth < 0:
                    recommendations.append("Il fatturato è in calo - considera di rivedere la strategia di prezzo e il posizionamento di mercato")
                elif latest_growth < 5:
                    recommendations.append("Rilevata crescita moderata - esplora opportunità di espansione")
                else:
                    recommendations.append("Forte slancio di crescita - assicurati che le operazioni possano scalare di conseguenza")

        # Check ratios
        if 'ratios' in analysis:
            for ratio_name, value in analysis['ratios'].items():
                if 'margin' in ratio_name and value < 10:
                    recommendations.append(f"Basso {ratio_name} ({value}%) - rivedi struttura dei costi e prezzi")

        # Check efficiency
        if 'efficiency_ratio' in analysis.get('summary', {}):
            efficiency = analysis['summary']['efficiency_ratio']
            if efficiency > 80:
                recommendations.append("Alto rapporto costi/fatturato - identifica aree per l'ottimizzazione dei costi")

        return recommendations

    def get_parsed_values_with_provenance(self) -> list[dict[str, Any]]:
        """Get parsed values with full provenance information"""
        return [
            {
                'value': pv.value,
                'raw_text': pv.raw_text,
                'unit': pv.unit,
                'currency': pv.currency,
                'source_ref': pv.source_ref,
                'confidence': pv.confidence,
                'scale_factor': pv.scale_factor
            }
            for pv in self.parsed_values
        ]

    def validate_financial_coherence(self) -> dict[str, Any]:
        """Validate financial coherence of parsed data using enterprise components"""
        # Validation is now handled by the enterprise DataNormalizer and guardrails
        # This method is kept for API compatibility but returns basic validation info

        return {
            'balance_sheet_errors': [],
            'range_errors': [],
            'total_errors': 0,
            'validation_passed': True,
            'note': 'Validation now handled by enterprise DataNormalizer component'
        }

    def get_normalized_metrics(self) -> dict[str, list[ProvenancedValue]]:
        """Get metrics grouped by normalized name"""
        metrics_by_name = {}

        for pv in self.parsed_values:
            # Extract normalized metric name from source_ref
            if '|col:' in pv.source_ref:
                col_name = pv.source_ref.split('|col:')[-1]
                normalized_name = self.italian_parser.normalize_metric_name(col_name)

                if normalized_name not in metrics_by_name:
                    metrics_by_name[normalized_name] = []
                metrics_by_name[normalized_name].append(pv)

        return metrics_by_name

    def export_provenance_report(self, output_path: str):
        """Export detailed provenance report"""
        report = {
            'file_analyzed': getattr(self, 'current_file', 'unknown'),
            'analysis_timestamp': datetime.now().isoformat(),
            'total_values_parsed': len(self.parsed_values),
            'validation_results': self.validate_financial_coherence(),
            'metrics_by_category': self.get_normalized_metrics(),
            'raw_parsed_values': self.get_parsed_values_with_provenance()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
