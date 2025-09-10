"""
Advanced Report Scheduler System
================================

Automated report generation and delivery with scheduling capabilities.
"""

from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from pathlib import Path
import sys
from typing import Any, Optional
import uuid

from src.core.security.multi_tenant_manager import MultiTenantManager

sys.path.append(str(Path(__file__).parent.parent.parent.parent / "services"))
from rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class ReportType(Enum):
    """Available report types."""
    USAGE_ANALYTICS = "usage_analytics"
    QUERY_INSIGHTS = "query_insights"
    DOCUMENT_STATS = "document_stats"
    PERFORMANCE_METRICS = "performance_metrics"
    FINANCIAL_SUMMARY = "financial_summary"
    CUSTOM_DASHBOARD = "custom_dashboard"

class ReportFormat(Enum):
    """Export formats."""
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"
    HTML = "html"
    CSV = "csv"

class ReportFrequency(Enum):
    """Scheduling frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_DEMAND = "on_demand"

class ReportDelivery(Enum):
    """Delivery methods."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    STORAGE = "storage"
    API = "api"

class ScheduledReport:
    """Configuration for a scheduled report."""

    def __init__(self, config: dict[str, Any]):
        self.id = config.get('id', str(uuid.uuid4()))
        self.name = config['name']
        self.tenant_id = config['tenant_id']
        self.report_type = ReportType(config['report_type'])
        self.format = ReportFormat(config.get('format', 'pdf'))
        self.frequency = ReportFrequency(config['frequency'])
        self.delivery = ReportDelivery(config.get('delivery', 'storage'))

        # Schedule configuration
        self.schedule_config = config.get('schedule', {})
        self.timezone = config.get('timezone', 'UTC')

        # Report parameters
        self.parameters = config.get('parameters', {})

        # Delivery configuration
        self.delivery_config = config.get('delivery_config', {})

        # Metadata
        self.created_at = datetime.fromisoformat(config.get('created_at', datetime.now().isoformat()))
        self.updated_at = datetime.fromisoformat(config.get('updated_at', datetime.now().isoformat()))
        self.last_run = config.get('last_run')
        self.next_run = config.get('next_run')
        self.enabled = config.get('enabled', True)
        self.run_count = config.get('run_count', 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'id': self.id,
            'name': self.name,
            'tenant_id': self.tenant_id,
            'report_type': self.report_type.value,
            'format': self.format.value,
            'frequency': self.frequency.value,
            'delivery': self.delivery.value,
            'schedule_config': self.schedule_config,
            'timezone': self.timezone,
            'parameters': self.parameters,
            'delivery_config': self.delivery_config,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_run': self.last_run,
            'next_run': self.next_run,
            'enabled': self.enabled,
            'run_count': self.run_count
        }

class ReportScheduler:
    """Advanced report scheduling and management system."""

    def __init__(self):
        """Initialize report scheduler."""
        self.reports_dir = Path("data/scheduled_reports")
        self.reports_dir.mkdir(exist_ok=True)

        self.outputs_dir = Path("data/report_outputs")
        self.outputs_dir.mkdir(exist_ok=True)

        # Load scheduled reports
        self.scheduled_reports: dict[str, ScheduledReport] = {}
        self._load_scheduled_reports()

        # Initialize services
        self.tenant_manager = MultiTenantManager()

    def _load_scheduled_reports(self):
        """Load scheduled reports from storage."""
        for report_file in self.reports_dir.glob("*.json"):
            try:
                with open(report_file) as f:
                    config = json.load(f)
                    report = ScheduledReport(config)
                    self.scheduled_reports[report.id] = report
            except Exception as e:
                logger.error(f"Failed to load report {report_file}: {e}")

    def create_scheduled_report(self, config: dict[str, Any]) -> ScheduledReport:
        """Create a new scheduled report."""
        report = ScheduledReport(config)

        # Calculate next run time
        report.next_run = self._calculate_next_run(report)

        # Save report configuration
        self._save_report_config(report)

        # Add to memory
        self.scheduled_reports[report.id] = report

        # Register with Celery scheduler if enabled
        if report.enabled:
            self._register_celery_task(report)

        logger.info(f"Created scheduled report: {report.name} ({report.id})")
        return report

    def update_scheduled_report(self, report_id: str, updates: dict[str, Any]) -> Optional[ScheduledReport]:
        """Update an existing scheduled report."""
        if report_id not in self.scheduled_reports:
            return None

        report = self.scheduled_reports[report_id]

        # Apply updates
        for key, value in updates.items():
            if hasattr(report, key):
                setattr(report, key, value)

        report.updated_at = datetime.now()

        # Recalculate next run if schedule changed
        if any(key in updates for key in ['frequency', 'schedule_config']):
            report.next_run = self._calculate_next_run(report)

        # Save updated configuration
        self._save_report_config(report)

        # Update Celery scheduler
        if report.enabled:
            self._register_celery_task(report)
        else:
            self._unregister_celery_task(report)

        logger.info(f"Updated scheduled report: {report.name}")
        return report

    def delete_scheduled_report(self, report_id: str) -> bool:
        """Delete a scheduled report."""
        if report_id not in self.scheduled_reports:
            return False

        report = self.scheduled_reports[report_id]

        # Unregister from Celery
        self._unregister_celery_task(report)

        # Remove configuration file
        config_file = self.reports_dir / f"{report_id}.json"
        if config_file.exists():
            config_file.unlink()

        # Remove from memory
        del self.scheduled_reports[report_id]

        logger.info(f"Deleted scheduled report: {report.name}")
        return True

    def run_report_now(self, report_id: str) -> dict[str, Any]:
        """Execute a report immediately."""
        if report_id not in self.scheduled_reports:
            return {'error': 'Report not found'}

        report = self.scheduled_reports[report_id]

        try:
            # Generate report
            result = self._generate_report(report)

            # Update run statistics
            report.last_run = datetime.now().isoformat()
            report.run_count += 1
            self._save_report_config(report)

            return {
                'success': True,
                'report_id': report_id,
                'output_path': result.get('output_path'),
                'generated_at': result.get('generated_at'),
                'size_bytes': result.get('size_bytes', 0)
            }

        except Exception as e:
            logger.error(f"Failed to generate report {report_id}: {e}")
            return {'error': str(e)}

    def get_scheduled_reports(self, tenant_id: Optional[str] = None) -> list[ScheduledReport]:
        """Get all scheduled reports, optionally filtered by tenant."""
        reports = list(self.scheduled_reports.values())

        if tenant_id:
            reports = [r for r in reports if r.tenant_id == tenant_id]

        return sorted(reports, key=lambda x: x.created_at, reverse=True)

    def get_report_history(self, report_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get execution history for a report."""
        history_file = self.outputs_dir / f"{report_id}_history.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file) as f:
                history = json.load(f)
                return history[-limit:] if limit else history
        except Exception as e:
            logger.error(f"Failed to load report history: {e}")
            return []

    def _generate_report(self, report: ScheduledReport) -> dict[str, Any]:
        """Generate a report based on configuration."""
        # Get tenant context
        tenant_context = self.tenant_manager.get_tenant(report.tenant_id)

        # Initialize report generator based on type
        if report.report_type == ReportType.USAGE_ANALYTICS:
            data = self._generate_usage_analytics(tenant_context, report.parameters)
        elif report.report_type == ReportType.QUERY_INSIGHTS:
            data = self._generate_query_insights(tenant_context, report.parameters)
        elif report.report_type == ReportType.DOCUMENT_STATS:
            data = self._generate_document_stats(tenant_context, report.parameters)
        elif report.report_type == ReportType.PERFORMANCE_METRICS:
            data = self._generate_performance_metrics(tenant_context, report.parameters)
        elif report.report_type == ReportType.FINANCIAL_SUMMARY:
            data = self._generate_financial_summary(tenant_context, report.parameters)
        elif report.report_type == ReportType.CUSTOM_DASHBOARD:
            data = self._generate_custom_dashboard(tenant_context, report.parameters)
        else:
            raise ValueError(f"Unknown report type: {report.report_type}")

        # Export in requested format
        output_path = self._export_report(report, data)

        # Deliver report
        self._deliver_report(report, output_path)

        # Log execution
        self._log_report_execution(report, output_path)

        return {
            'output_path': str(output_path),
            'generated_at': datetime.now().isoformat(),
            'size_bytes': output_path.stat().st_size if output_path.exists() else 0
        }

    def _generate_usage_analytics(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate usage analytics report data."""
        # Get date range
        end_date = datetime.now()
        days = parameters.get('days', 30)
        start_date = end_date - timedelta(days=days)

        # Mock data - in production, get from actual analytics
        return {
            'title': f'Usage Analytics - {tenant_context.organization}',
            'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}',
            'metrics': {
                'total_queries': 1250,
                'unique_users': 45,
                'documents_processed': 320,
                'avg_response_time': '0.8s',
                'success_rate': '98.4%'
            },
            'daily_usage': [
                {'date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                 'queries': 30 + (i % 20)} for i in range(days)
            ],
            'top_queries': [
                'Revenue analysis Q4',
                'Profit margin trends',
                'Customer segmentation',
                'Market share analysis',
                'Cost optimization'
            ]
        }

    def _generate_query_insights(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate query insights report data."""
        return {
            'title': f'Query Insights - {tenant_context.organization}',
            'summary': {
                'total_queries': 890,
                'avg_tokens': 45,
                'most_common_topics': ['finance', 'sales', 'operations'],
                'peak_hours': ['09:00-11:00', '14:00-16:00']
            },
            'query_categories': {
                'Financial Analysis': 35,
                'Business Intelligence': 28,
                'Operational Queries': 22,
                'Strategic Planning': 15
            },
            'performance_metrics': {
                'fast_queries': 756,  # < 1s
                'medium_queries': 102,  # 1-3s
                'slow_queries': 32   # > 3s
            }
        }

    def _generate_document_stats(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate document statistics report."""
        rag_engine = RAGEngine(tenant_context=tenant_context)
        stats = rag_engine.get_index_stats()

        return {
            'title': f'Document Statistics - {tenant_context.organization}',
            'overview': {
                'total_documents': stats.get('total_vectors', 0),
                'index_size_mb': stats.get('index_size_mb', 0),
                'collections': stats.get('collections_count', 1)
            },
            'document_types': {
                'PDF': 45,
                'CSV': 23,
                'TXT': 12,
                'DOCX': 8,
                'JSON': 5
            },
            'recent_activity': [
                {'date': '2024-01-15', 'action': 'Added', 'count': 5},
                {'date': '2024-01-14', 'action': 'Updated', 'count': 2},
                {'date': '2024-01-13', 'action': 'Added', 'count': 8}
            ]
        }

    def _generate_performance_metrics(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate performance metrics report."""
        return {
            'title': f'Performance Metrics - {tenant_context.organization}',
            'system_health': {
                'uptime': '99.8%',
                'avg_response_time': '0.75s',
                'error_rate': '0.2%',
                'throughput': '150 queries/hour'
            },
            'resource_usage': {
                'cpu_avg': 45.2,
                'memory_avg': 68.5,
                'disk_usage': 78.3,
                'network_io': 'Normal'
            },
            'trends': {
                'response_time_trend': 'Improving',
                'error_rate_trend': 'Stable',
                'usage_trend': 'Growing'
            }
        }

    def _generate_financial_summary(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate financial summary report."""
        return {
            'title': f'Financial Summary - {tenant_context.organization}',
            'key_metrics': {
                'revenue': 1250000,
                'profit_margin': 23.5,
                'growth_rate': 15.2,
                'roi': 18.7
            },
            'quarterly_comparison': [
                {'quarter': 'Q4 2023', 'revenue': 1250000, 'profit': 293750},
                {'quarter': 'Q3 2023', 'revenue': 1180000, 'profit': 270200},
                {'quarter': 'Q2 2023', 'revenue': 1090000, 'profit': 245700}
            ],
            'insights': [
                'Revenue growth accelerated in Q4',
                'Profit margin improved by 2.1%',
                'Operating costs remained stable'
            ]
        }

    def _generate_custom_dashboard(self, tenant_context, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate custom dashboard report."""
        dashboard_id = parameters.get('dashboard_id')

        return {
            'title': f'Custom Dashboard Export - {dashboard_id}',
            'widgets': [
                {'type': 'metric', 'title': 'Total Users', 'value': 245},
                {'type': 'chart', 'title': 'Usage Trend', 'data': [10, 15, 12, 18, 20]},
                {'type': 'table', 'title': 'Top Queries', 'rows': 5}
            ],
            'exported_at': datetime.now().isoformat(),
            'tenant': tenant_context.organization
        }

    def _export_report(self, report: ScheduledReport, data: dict[str, Any]) -> Path:
        """Export report in the requested format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.name}_{timestamp}"

        if report.format == ReportFormat.PDF:
            return self._export_pdf(report, data, filename)
        elif report.format == ReportFormat.EXCEL:
            return self._export_excel(report, data, filename)
        elif report.format == ReportFormat.JSON:
            return self._export_json(report, data, filename)
        elif report.format == ReportFormat.HTML:
            return self._export_html(report, data, filename)
        elif report.format == ReportFormat.CSV:
            return self._export_csv(report, data, filename)
        else:
            raise ValueError(f"Unsupported format: {report.format}")

    def _export_pdf(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Export report as PDF."""
        try:
            from src.presentation.streamlit.pdf_exporter import PDFExporter

            pdf_exporter = PDFExporter()
            pdf_buffer = pdf_exporter.export_analytics_report(data, report.parameters)

            output_path = self.outputs_dir / f"{filename}.pdf"
            with open(output_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())

            return output_path

        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            # Fallback to simple text export
            return self._export_text(report, data, filename)

    def _export_excel(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Export report as Excel."""
        import pandas as pd

        output_path = self.outputs_dir / f"{filename}.xlsx"

        with pd.ExcelWriter(output_path) as writer:
            # Summary sheet
            summary_data = []
            if 'metrics' in data:
                for key, value in data['metrics'].items():
                    summary_data.append({'Metric': key, 'Value': value})
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

            # Detailed data sheets
            if 'daily_usage' in data:
                pd.DataFrame(data['daily_usage']).to_excel(writer, sheet_name='Daily Usage', index=False)

            if 'query_categories' in data:
                categories_data = [{'Category': k, 'Count': v} for k, v in data['query_categories'].items()]
                pd.DataFrame(categories_data).to_excel(writer, sheet_name='Categories', index=False)

        return output_path

    def _export_json(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Export report as JSON."""
        output_path = self.outputs_dir / f"{filename}.json"

        export_data = {
            'report_info': {
                'id': report.id,
                'name': report.name,
                'type': report.report_type.value,
                'generated_at': datetime.now().isoformat(),
                'tenant_id': report.tenant_id
            },
            'data': data
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        return output_path

    def _export_html(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Export report as HTML."""
        output_path = self.outputs_dir / f"{filename}.html"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{data.get('title', report.name)}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .metric {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1>{data.get('title', report.name)}</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>Key Metrics</h2>
            {self._format_metrics_html(data.get('metrics', {}))}

            <h2>Details</h2>
            <pre>{json.dumps(data, indent=2)}</pre>
        </body>
        </html>
        """

        with open(output_path, 'w') as f:
            f.write(html_content)

        return output_path

    def _export_csv(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Export report as CSV."""
        import pandas as pd

        output_path = self.outputs_dir / f"{filename}.csv"

        # Convert data to flat structure for CSV
        rows = []
        if 'metrics' in data:
            for key, value in data['metrics'].items():
                rows.append({'Category': 'Metrics', 'Key': key, 'Value': value})

        if 'daily_usage' in data:
            for item in data['daily_usage']:
                rows.append({'Category': 'Daily Usage', 'Key': item['date'], 'Value': item['queries']})

        pd.DataFrame(rows).to_csv(output_path, index=False)
        return output_path

    def _export_text(self, report: ScheduledReport, data: dict[str, Any], filename: str) -> Path:
        """Fallback text export."""
        output_path = self.outputs_dir / f"{filename}.txt"

        with open(output_path, 'w') as f:
            f.write(f"Report: {data.get('title', report.name)}\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            f.write(json.dumps(data, indent=2))

        return output_path

    def _format_metrics_html(self, metrics: dict[str, Any]) -> str:
        """Format metrics as HTML."""
        html = ""
        for key, value in metrics.items():
            html += f'<div class="metric"><strong>{key}:</strong> {value}</div>'
        return html

    def _deliver_report(self, report: ScheduledReport, output_path: Path):
        """Deliver report based on delivery configuration."""
        if report.delivery == ReportDelivery.EMAIL:
            self._deliver_email(report, output_path)
        elif report.delivery == ReportDelivery.WEBHOOK:
            self._deliver_webhook(report, output_path)
        elif report.delivery == ReportDelivery.API:
            self._deliver_api(report, output_path)
        # STORAGE is default - just keep the file

    def _deliver_email(self, report: ScheduledReport, output_path: Path):
        """Deliver report via email."""
        # TODO: Implement email delivery
        logger.info(f"Would send report {report.name} to email")

    def _deliver_webhook(self, report: ScheduledReport, output_path: Path):
        """Deliver report via webhook."""
        # TODO: Implement webhook delivery
        logger.info(f"Would send report {report.name} to webhook")

    def _deliver_api(self, report: ScheduledReport, output_path: Path):
        """Make report available via API."""
        # TODO: Implement API delivery
        logger.info(f"Report {report.name} available via API")

    def _log_report_execution(self, report: ScheduledReport, output_path: Path):
        """Log report execution to history."""
        history_file = self.outputs_dir / f"{report.id}_history.json"

        execution_log = {
            'timestamp': datetime.now().isoformat(),
            'report_id': report.id,
            'output_path': str(output_path),
            'size_bytes': output_path.stat().st_size if output_path.exists() else 0,
            'format': report.format.value,
            'success': True
        }

        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file) as f:
                    history = json.load(f)
            except:
                history = []

        # Add new execution
        history.append(execution_log)

        # Keep only last 100 executions
        history = history[-100:]

        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _calculate_next_run(self, report: ScheduledReport) -> str:
        """Calculate next run time based on frequency."""
        now = datetime.now()

        if report.frequency == ReportFrequency.DAILY:
            next_run = now + timedelta(days=1)
        elif report.frequency == ReportFrequency.WEEKLY:
            next_run = now + timedelta(weeks=1)
        elif report.frequency == ReportFrequency.MONTHLY:
            next_run = now + timedelta(days=30)
        elif report.frequency == ReportFrequency.QUARTERLY:
            next_run = now + timedelta(days=90)
        else:  # ON_DEMAND
            return None

        return next_run.isoformat()

    def _save_report_config(self, report: ScheduledReport):
        """Save report configuration to file."""
        config_file = self.reports_dir / f"{report.id}.json"
        with open(config_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

    def _register_celery_task(self, report: ScheduledReport):
        """Register report with Celery scheduler."""
        # TODO: Implement Celery task registration
        logger.info(f"Would register Celery task for report {report.name}")

    def _unregister_celery_task(self, report: ScheduledReport):
        """Unregister report from Celery scheduler."""
        # TODO: Implement Celery task unregistration
        logger.info(f"Would unregister Celery task for report {report.name}")
