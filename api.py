"""
FastAPI Application Entry Point
==============================

This is the main entry point for the FastAPI application.
It imports the app from the proper API module location.

Usage:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Or with uv:
    uv run uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

from src.presentation.api.main import app

__all__ = ["app"]
