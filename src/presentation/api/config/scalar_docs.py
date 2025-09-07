"""
Scalar API Documentation Configuration
====================================

This module configures Scalar API documentation alongside Swagger UI.
Scalar provides a modern, interactive API documentation experience.
"""

from fastapi import FastAPI
try:
    from scalar_fastapi import get_scalar_api_reference
except ImportError:
    # Fallback if scalar_fastapi is not available or has different API
    def get_scalar_api_reference(*args, **kwargs):
        return """
        <html>
        <head><title>Documentazione API</title></head>
        <body>
        <h1>Documentazione Scalar</h1>
        <p>Scalar FastAPI non disponibile. Usa <a href="/docs">Swagger UI</a> invece.</p>
        </body>
        </html>
        """

def add_scalar_docs(app: FastAPI) -> None:
    """
    Add Scalar API documentation to FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.get("/scalar", include_in_schema=False)
    async def scalar_html():
        """
        Scalar API Documentation endpoint.
        
        Provides modern, interactive API documentation as an alternative to Swagger UI.
        """
        return get_scalar_api_reference(
            title="API RAG Business Intelligence",
            openapi_url="/openapi.json"
        )