"""Data versioning infrastructure with DVC integration."""

from .dvc_manager import DataVersion, DVCManager, ModelSnapshot

__all__ = ['DVCManager', 'ModelSnapshot', 'DataVersion']
