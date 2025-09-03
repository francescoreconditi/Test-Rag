"""LLM Service for intelligent analysis and insights generation."""

from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime
from openai import OpenAI

from config.settings import settings

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
    
    def generate_business_insights(self, csv_analysis: Dict[str, Any], 
                                  rag_context: Optional[str] = None) -> str:
        """Generate comprehensive business insights from analysis data."""
        try:
            # Prepare the prompt
            prompt = self._build_insights_prompt(csv_analysis, rag_context)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior business analyst providing strategic insights based on financial data and business documents. Provide clear, actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return f"Unable to generate insights: {str(e)}"
    
    def _build_insights_prompt(self, csv_analysis: Dict[str, Any], rag_context: Optional[str]) -> str:
        """Build comprehensive prompt for insights generation."""
        prompt_parts = ["Please analyze the following business data and provide strategic insights:\n"]
        
        # Add CSV analysis data
        if 'summary' in csv_analysis:
            prompt_parts.append("\n## Financial Metrics:")
            for key, value in csv_analysis['summary'].items():
                prompt_parts.append(f"- {key}: {value}")
        
        if 'trends' in csv_analysis:
            prompt_parts.append("\n## Trends:")
            if 'yoy_growth' in csv_analysis['trends']:
                for growth in csv_analysis['trends']['yoy_growth']:
                    prompt_parts.append(
                        f"- Year {growth['year']}: {growth['growth_percentage']}% growth "
                        f"(change: {growth['absolute_change']:,.2f})"
                    )
        
        if 'ratios' in csv_analysis:
            prompt_parts.append("\n## Financial Ratios:")
            for ratio, value in csv_analysis['ratios'].items():
                prompt_parts.append(f"- {ratio}: {value}%")
        
        if 'insights' in csv_analysis:
            prompt_parts.append("\n## Initial Observations:")
            for insight in csv_analysis['insights']:
                prompt_parts.append(f"- {insight}")
        
        # Add RAG context if available
        if rag_context:
            prompt_parts.append(f"\n## Additional Context from Documents:\n{rag_context}")
        
        prompt_parts.append("""
        
Please provide:
1. Executive Summary (2-3 sentences)
2. Key Strengths (3 bullet points)
3. Areas of Concern (3 bullet points)
4. Strategic Recommendations (5 specific actions)
5. Risk Assessment
6. 12-Month Outlook
        """)
        
        return '\n'.join(prompt_parts)
    
    def compare_periods_narrative(self, comparison_data: Dict[str, Any]) -> str:
        """Generate narrative comparison between periods."""
        try:
            prompt = self._build_comparison_prompt(comparison_data)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst explaining period-over-period changes in business metrics."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens // 2
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating comparison narrative: {str(e)}")
            return "Unable to generate comparison narrative."
    
    def _build_comparison_prompt(self, comparison_data: Dict[str, Any]) -> str:
        """Build prompt for period comparison."""
        prompt_parts = ["Analyze the following period comparison:\n"]
        
        if 'differences' in comparison_data:
            prompt_parts.append("\n## Absolute Changes:")
            for metric, diff in comparison_data['differences'].items():
                prompt_parts.append(f"- {metric}: {diff:+,.2f}")
        
        if 'percentage_changes' in comparison_data:
            prompt_parts.append("\n## Percentage Changes:")
            for metric, pct in comparison_data['percentage_changes'].items():
                prompt_parts.append(f"- {metric}: {pct:+.1f}%")
        
        prompt_parts.append("""
        
Please provide a clear, concise narrative that:
1. Highlights the most significant changes
2. Explains potential causes
3. Identifies patterns or correlations
4. Suggests implications for the business
        """)
        
        return '\n'.join(prompt_parts)
    
    def answer_business_question(self, question: str, context: Dict[str, Any]) -> str:
        """Answer specific business questions using available context."""
        try:
            # Build context-aware prompt
            context_str = json.dumps(context, indent=2, default=str)
            
            prompt = f"""
Based on the following business data and analysis:

{context_str}

Question: {question}

Please provide a detailed, data-driven answer that:
1. Directly addresses the question
2. References specific metrics from the data
3. Provides actionable insights where relevant
4. Acknowledges any limitations in the available data
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business intelligence expert. Answer questions precisely using the provided data, and clearly state when information is insufficient."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Unable to process question: {str(e)}"
    
    def generate_executive_report(self, 
                                 csv_analysis: Dict[str, Any],
                                 rag_insights: Optional[str] = None,
                                 custom_sections: Optional[List[str]] = None) -> str:
        """Generate comprehensive executive report."""
        try:
            sections = custom_sections or [
                "Executive Summary",
                "Financial Performance",
                "Operational Highlights",
                "Market Position",
                "Recommendations",
                "Next Steps"
            ]
            
            prompt = f"""
Generate a professional executive report based on the following data:

## Financial Analysis:
{json.dumps(csv_analysis, indent=2, default=str)}

## Document Insights:
{rag_insights or 'No additional document context available'}

Please create a comprehensive report with these sections:
{chr(10).join(f'- {section}' for section in sections)}

Format the report professionally with clear headers and bullet points where appropriate.
Include specific metrics and percentages to support all statements.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a C-level executive consultant preparing strategic reports for board meetings. Be concise yet comprehensive, data-driven, and action-oriented."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature - 0.2,  # Lower temperature for more focused output
                max_tokens=self.max_tokens * 2  # Allow longer reports
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating executive report: {str(e)}")
            return f"Unable to generate report: {str(e)}"
    
    def identify_anomalies_explanation(self, anomalies: List[Dict[str, Any]]) -> str:
        """Generate explanations for detected anomalies."""
        try:
            if not anomalies:
                return "No significant anomalies detected in the current dataset."
            
            prompt = f"""
Analyze the following anomalies detected in business data:

{json.dumps(anomalies, indent=2, default=str)}

For each anomaly, provide:
1. Possible explanations (both positive and negative scenarios)
2. Recommended investigation steps
3. Potential business impact
4. Suggested immediate actions
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a risk analyst specializing in business anomaly detection and investigation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error explaining anomalies: {str(e)}")
            return "Unable to analyze anomalies."
    
    def generate_action_items(self, analysis: Dict[str, Any], priority_count: int = 10) -> List[Dict[str, str]]:
        """Generate prioritized action items from analysis."""
        try:
            prompt = f"""
Based on this business analysis:

{json.dumps(analysis, indent=2, default=str)}

Generate exactly {priority_count} specific, actionable items that the business should pursue.

Format your response as a JSON array with objects containing:
- "action": specific action to take
- "priority": "high", "medium", or "low"
- "timeline": suggested timeframe (e.g., "immediate", "30 days", "Q2 2024")
- "impact": expected business impact
- "owner": suggested department or role

Focus on realistic, implementable actions that directly address the data insights.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business strategist creating actionable recommendations. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            content = response.choices[0].message.content
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return []
            
        except Exception as e:
            logger.error(f"Error generating action items: {str(e)}")
            return []