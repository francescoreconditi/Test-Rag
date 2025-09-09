"""
Analytics API for Advanced Reporting
====================================

RESTful API for analytics data, metrics, and reporting functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
from pathlib import Path

from src.core.security.multi_tenant_manager import MultiTenantManager, TenantSession
from src.application.services.report_scheduler import ReportScheduler, ReportType, ReportFormat, ReportFrequency
from src.presentation.ui.dashboard_embed import DashboardEmbed
from services.rag_engine import RAGEngine

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Pydantic models for API requests/responses
class AnalyticsQuery(BaseModel):
    """Query parameters for analytics data."""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    granularity: str = "day"  # hour, day, week, month
    metrics: List[str] = ["queries", "documents", "users"]
    filters: Dict[str, Any] = {}

class ReportRequest(BaseModel):
    """Request to generate a report."""
    name: str
    report_type: str
    format: str = "json"
    parameters: Dict[str, Any] = {}
    delivery_config: Dict[str, Any] = {}

class ScheduledReportRequest(BaseModel):
    """Request to create scheduled report."""
    name: str
    report_type: str
    format: str = "pdf"
    frequency: str = "weekly"
    delivery: str = "storage"
    parameters: Dict[str, Any] = {}
    delivery_config: Dict[str, Any] = {}
    schedule_config: Dict[str, Any] = {}
    enabled: bool = True

class DashboardEmbedRequest(BaseModel):
    """Request to create dashboard embed."""
    name: str
    dashboard_id: str
    width: str = "100%"
    height: str = "600px"
    theme: str = "light"
    auto_refresh: bool = False
    refresh_interval: int = 300
    public_access: bool = False
    allowed_domains: List[str] = []

# Initialize services
tenant_manager = MultiTenantManager()
report_scheduler = ReportScheduler()
dashboard_embed = DashboardEmbed()

async def get_current_tenant(authorization: str = Header(None)) -> TenantSession:
    """Get current tenant from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    session = await tenant_manager.authenticate_tenant_request(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return session

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@router.get("/metrics/overview")
async def get_metrics_overview(
    session: TenantSession = Depends(get_current_tenant),
    days: int = Query(30, description="Number of days to look back")
):
    """Get overview metrics for tenant."""
    try:
        # Get tenant context
        tenant_context = tenant_manager.get_tenant(session.tenant_id)
        if not tenant_context:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        # Get usage statistics
        usage = tenant_manager.get_tenant_usage(session.tenant_id)
        
        # Get RAG engine statistics
        rag_engine = RAGEngine(tenant_context=tenant_context)
        index_stats = rag_engine.get_index_stats()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Compile overview metrics
        overview = {
            "tenant_info": {
                "tenant_id": session.tenant_id,
                "organization": tenant_context.organization,
                "tier": tenant_context.tier.value,
                "status": tenant_context.status.value
            },
            "usage_metrics": {
                "documents_today": usage.get('documents_today', 0),
                "documents_this_month": usage.get('documents_this_month', 0),
                "queries_today": usage.get('queries_today', 0),
                "storage_mb": usage.get('storage_mb', 0)
            },
            "index_metrics": {
                "total_vectors": index_stats.get('total_vectors', 0),
                "index_size_mb": index_stats.get('index_size_mb', 0),
                "collections_count": index_stats.get('collections_count', 1)
            },
            "resource_limits": {
                "max_documents_per_month": tenant_context.resource_limits.max_documents_per_month,
                "max_storage_gb": tenant_context.resource_limits.max_storage_gb,
                "max_queries_per_day": tenant_context.resource_limits.max_queries_per_day,
                "max_concurrent_users": tenant_context.resource_limits.max_concurrent_users
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            }
        }
        
        return overview
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_analytics(
    query: AnalyticsQuery,
    session: TenantSession = Depends(get_current_tenant)
):
    """Query analytics data with flexible parameters."""
    try:
        # Parse date range
        if query.start_date:
            start_date = datetime.fromisoformat(query.start_date.replace('Z', '+00:00'))
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        if query.end_date:
            end_date = datetime.fromisoformat(query.end_date.replace('Z', '+00:00'))
        else:
            end_date = datetime.now()
        
        # Generate mock analytics data based on query
        # In production, this would query actual analytics database
        analytics_data = {
            "query_info": {
                "tenant_id": session.tenant_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "granularity": query.granularity,
                "metrics": query.metrics
            },
            "data": {}
        }
        
        # Generate data for each requested metric
        days_range = (end_date - start_date).days
        
        if "queries" in query.metrics:
            analytics_data["data"]["queries"] = {
                "total": 1250,
                "daily_average": 42,
                "trend": "increasing",
                "by_period": [
                    {
                        "date": (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                        "count": 35 + (i % 15),
                        "success_rate": 0.95 + (0.04 * (i % 10) / 10)
                    }
                    for i in range(min(days_range, 30))
                ]
            }
        
        if "documents" in query.metrics:
            analytics_data["data"]["documents"] = {
                "total": 342,
                "new_this_period": 23,
                "by_type": {
                    "pdf": 145,
                    "csv": 89,
                    "txt": 67,
                    "docx": 41
                },
                "by_period": [
                    {
                        "date": (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                        "added": max(0, 3 + (i % 7) - 2),
                        "processed": max(0, 4 + (i % 5))
                    }
                    for i in range(min(days_range, 30))
                ]
            }
        
        if "users" in query.metrics:
            analytics_data["data"]["users"] = {
                "total_active": 47,
                "new_this_period": 8,
                "retention_rate": 0.85,
                "by_period": [
                    {
                        "date": (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
                        "active_users": 12 + (i % 8),
                        "sessions": 28 + (i % 15)
                    }
                    for i in range(min(days_range, 30))
                ]
            }
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
async def list_reports(
    session: TenantSession = Depends(get_current_tenant),
    limit: int = Query(50, description="Maximum number of reports to return")
):
    """List available reports for tenant."""
    try:
        reports = report_scheduler.get_scheduled_reports(session.tenant_id)
        
        return {
            "total": len(reports),
            "reports": [
                {
                    "id": report.id,
                    "name": report.name,
                    "type": report.report_type.value,
                    "format": report.format.value,
                    "frequency": report.frequency.value,
                    "enabled": report.enabled,
                    "last_run": report.last_run,
                    "next_run": report.next_run,
                    "run_count": report.run_count,
                    "created_at": report.created_at.isoformat()
                }
                for report in reports[:limit]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/generate")
async def generate_report(
    request: ReportRequest,
    session: TenantSession = Depends(get_current_tenant)
):
    """Generate a report on-demand."""
    try:
        # Create temporary scheduled report for generation
        config = {
            "name": request.name,
            "tenant_id": session.tenant_id,
            "report_type": request.report_type,
            "format": request.format,
            "frequency": "on_demand",
            "parameters": request.parameters,
            "delivery_config": request.delivery_config,
            "enabled": True
        }
        
        # Generate report
        scheduled_report = report_scheduler.create_scheduled_report(config)
        result = report_scheduler.run_report_now(scheduled_report.id)
        
        if result.get('success'):
            return {
                "success": True,
                "report_id": scheduled_report.id,
                "output_path": result.get('output_path'),
                "generated_at": result.get('generated_at'),
                "size_bytes": result.get('size_bytes', 0),
                "download_url": f"/api/v1/analytics/reports/{scheduled_report.id}/download"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Report generation failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/schedule")
async def create_scheduled_report(
    request: ScheduledReportRequest,
    session: TenantSession = Depends(get_current_tenant)
):
    """Create a new scheduled report."""
    try:
        config = {
            "name": request.name,
            "tenant_id": session.tenant_id,
            "report_type": request.report_type,
            "format": request.format,
            "frequency": request.frequency,
            "delivery": request.delivery,
            "parameters": request.parameters,
            "delivery_config": request.delivery_config,
            "schedule_config": request.schedule_config,
            "enabled": request.enabled
        }
        
        scheduled_report = report_scheduler.create_scheduled_report(config)
        
        return {
            "success": True,
            "report_id": scheduled_report.id,
            "name": scheduled_report.name,
            "next_run": scheduled_report.next_run,
            "created_at": scheduled_report.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    session: TenantSession = Depends(get_current_tenant)
):
    """Download a generated report."""
    try:
        # Check if report belongs to tenant
        reports = report_scheduler.get_scheduled_reports(session.tenant_id)
        report = next((r for r in reports if r.id == report_id), None)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Find the latest report output
        outputs_dir = Path("data/report_outputs")
        report_files = list(outputs_dir.glob(f"{report.name}_*"))
        
        if not report_files:
            raise HTTPException(status_code=404, detail="No report output found")
        
        # Get the latest file
        latest_file = max(report_files, key=lambda f: f.stat().st_mtime)
        
        return FileResponse(
            path=latest_file,
            filename=latest_file.name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/embeds")
async def list_dashboard_embeds(
    session: TenantSession = Depends(get_current_tenant)
):
    """List dashboard embeds for tenant."""
    try:
        embeds = dashboard_embed.list_embeds(session.tenant_id)
        
        return {
            "total": len(embeds),
            "embeds": [
                {
                    "id": embed.id,
                    "name": embed.name,
                    "dashboard_id": embed.dashboard_id,
                    "theme": embed.theme,
                    "public_access": embed.public_access,
                    "access_count": embed.access_count,
                    "last_accessed": embed.last_accessed,
                    "created_at": embed.created_at.isoformat(),
                    "embed_url": f"/embed/{embed.id}"
                }
                for embed in embeds
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embeds")
async def create_dashboard_embed(
    request: DashboardEmbedRequest,
    session: TenantSession = Depends(get_current_tenant)
):
    """Create a new dashboard embed."""
    try:
        config = {
            "name": request.name,
            "tenant_id": session.tenant_id,
            "dashboard_id": request.dashboard_id,
            "width": request.width,
            "height": request.height,
            "theme": request.theme,
            "auto_refresh": request.auto_refresh,
            "refresh_interval": request.refresh_interval,
            "public_access": request.public_access,
            "allowed_domains": request.allowed_domains,
            "api_key_required": not request.public_access
        }
        
        embed_config = dashboard_embed.create_embed(config)
        embed_code = dashboard_embed.generate_embed_code(embed_config.id)
        
        return {
            "success": True,
            "embed_id": embed_config.id,
            "name": embed_config.name,
            "embed_url": embed_code['embed_url'],
            "iframe_code": embed_code['iframe'],
            "created_at": embed_config.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/embeds/{embed_id}/code")
async def get_embed_code(
    embed_id: str,
    session: TenantSession = Depends(get_current_tenant),
    format: str = Query("iframe", description="Code format: iframe, javascript, react")
):
    """Get embed code for dashboard."""
    try:
        # Verify embed belongs to tenant
        embeds = dashboard_embed.list_embeds(session.tenant_id)
        embed_config = next((e for e in embeds if e.id == embed_id), None)
        
        if not embed_config:
            raise HTTPException(status_code=404, detail="Embed not found")
        
        embed_code = dashboard_embed.generate_embed_code(embed_id)
        
        if format not in embed_code:
            raise HTTPException(status_code=400, detail=f"Invalid format: {format}")
        
        return {
            "embed_id": embed_id,
            "format": format,
            "code": embed_code[format],
            "embed_url": embed_code['embed_url']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/embeds/{embed_id}/analytics")
async def get_embed_analytics(
    embed_id: str,
    session: TenantSession = Depends(get_current_tenant)
):
    """Get analytics for specific embed."""
    try:
        # Verify embed belongs to tenant
        embeds = dashboard_embed.list_embeds(session.tenant_id)
        embed_config = next((e for e in embeds if e.id == embed_id), None)
        
        if not embed_config:
            raise HTTPException(status_code=404, detail="Embed not found")
        
        analytics = dashboard_embed.get_embed_analytics(embed_id)
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/formats")
async def get_export_formats():
    """Get available export formats."""
    return {
        "formats": [
            {
                "id": "pdf",
                "name": "PDF Report",
                "description": "Professional PDF report with charts and formatting",
                "mime_type": "application/pdf"
            },
            {
                "id": "excel",
                "name": "Excel Spreadsheet",
                "description": "Structured data in Excel format with multiple sheets",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            {
                "id": "json",
                "name": "JSON Data",
                "description": "Raw data in JSON format for API integration",
                "mime_type": "application/json"
            },
            {
                "id": "csv",
                "name": "CSV File",
                "description": "Comma-separated values for data analysis",
                "mime_type": "text/csv"
            },
            {
                "id": "html",
                "name": "HTML Report",
                "description": "Web-ready HTML report with embedded styling",
                "mime_type": "text/html"
            }
        ]
    }

@router.get("/templates")
async def list_report_templates(
    session: TenantSession = Depends(get_current_tenant)
):
    """List available report templates."""
    return {
        "templates": [
            {
                "id": "usage_analytics",
                "name": "Usage Analytics",
                "description": "Comprehensive usage statistics and trends",
                "parameters": ["days", "include_charts", "granularity"]
            },
            {
                "id": "query_insights", 
                "name": "Query Insights",
                "description": "Analysis of query patterns and performance",
                "parameters": ["period", "top_n", "include_categories"]
            },
            {
                "id": "document_stats",
                "name": "Document Statistics",
                "description": "Document indexing and management statistics",
                "parameters": ["include_types", "show_recent_activity"]
            },
            {
                "id": "performance_metrics",
                "name": "Performance Metrics",
                "description": "System performance and health metrics",
                "parameters": ["include_trends", "show_alerts"]
            },
            {
                "id": "financial_summary",
                "name": "Financial Summary",
                "description": "Financial analysis and key metrics",
                "parameters": ["quarters", "include_comparisons", "show_projections"]
            },
            {
                "id": "custom_dashboard",
                "name": "Custom Dashboard Export",
                "description": "Export of custom dashboard configuration",
                "parameters": ["dashboard_id", "include_data"]
            }
        ]
    }