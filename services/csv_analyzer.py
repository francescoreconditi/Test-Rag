"""CSV Data Analyzer module for financial and business data analysis."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
from datetime import datetime


class CSVAnalyzer:
    """Analyzes CSV data for financial and business metrics."""
    
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.comparison_data: Optional[pd.DataFrame] = None
        self.metrics_cache: Dict[str, Any] = {}
    
    def load_csv(self, file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """Load CSV file and perform initial preprocessing."""
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            # Try to parse date columns
            for col in df.columns:
                if 'data' in col.lower() or 'date' in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except:
                        pass
            # Convert numeric columns
            for col in df.columns:
                if df[col].dtype == 'object':
                    try:
                        df[col] = pd.to_numeric(df[col].str.replace(',', '').str.replace('€', '').str.replace('$', ''))
                    except:
                        pass
            
            self.data = df
            return df
        except Exception as e:
            raise ValueError(f"Error loading CSV: {str(e)}")
    
    def analyze_balance_sheet(self, df: pd.DataFrame, year_column: str = 'anno', 
                            revenue_column: str = 'fatturato') -> Dict[str, Any]:
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
    
    def compare_periods(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                        key_metrics: List[str]) -> Dict[str, Any]:
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
    
    def calculate_kpis(self, df: pd.DataFrame) -> Dict[str, float]:
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
    
    def export_analysis(self, analysis: Dict[str, Any], output_path: str):
        """Export analysis results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
    
    def get_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
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