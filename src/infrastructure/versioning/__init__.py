"""Data versioning infrastructure with DVC integration."""

from .dvc_manager import DVCManager, ModelSnapshot, DataVersion

__all__ = ['DVCManager', 'ModelSnapshot', 'DataVersion']