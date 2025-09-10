# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Data Versioning con DVC per modelli e artefatti
# ============================================

"""
DVC Manager for data and model versioning in RAG Enterprise system.
Handles automatic snapshots, rollbacks, and A/B testing of ML artifacts.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import subprocess
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class ModelSnapshot:
    """Information about a model snapshot."""
    version_tag: str
    timestamp: str
    artifacts: dict[str, str]
    performance_metrics: dict[str, float]
    description: str
    git_commit: Optional[str] = None

@dataclass
class DataVersion:
    """Information about a data version."""
    path: str
    dvc_file: str
    version_hash: str
    size_bytes: int
    created_at: str

class DVCManager:
    """
    Enterprise DVC Manager for versioning ML models, datasets, and configurations.
    Integrates with Git for complete reproducibility.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.dvc_dir = self.repo_path / ".dvc"
        self.snapshots_dir = self.repo_path / "snapshots"
        self.models_dir = self.repo_path / "models"
        self.data_dir = self.repo_path / "data"

        # Create directories if they don't exist
        self.snapshots_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        self._ensure_dvc_initialized()

    def _ensure_dvc_initialized(self):
        """Ensure DVC is initialized in the repository."""
        try:
            if not self.dvc_dir.exists():
                logger.info("Initializing DVC repository")
                self._run_command(["dvc", "init"])
                self._run_command(["git", "add", ".dvc"])
                self._run_command(["git", "commit", "-m", "Initialize DVC"])
            else:
                logger.debug("DVC already initialized")
        except Exception as e:
            logger.error(f"Failed to initialize DVC: {e}")
            raise

    def _run_command(self, command: list[str]) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"Command succeeded: {' '.join(command)}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr}")
            raise

    def add_dataset(self, data_path: str, description: str = "") -> DataVersion:
        """
        Add dataset to DVC tracking.

        Args:
            data_path: Path to the data file/directory
            description: Description of the dataset

        Returns:
            DataVersion information
        """
        try:
            data_path = Path(data_path)
            if not data_path.exists():
                raise FileNotFoundError(f"Data path does not exist: {data_path}")

            # Add to DVC
            self._run_command(["dvc", "add", str(data_path)])

            # Get DVC file info
            dvc_file = f"{data_path}.dvc"

            # Get version hash from DVC
            self._run_command(["dvc", "status", str(data_path)])

            # Calculate size
            if data_path.is_file():
                size_bytes = data_path.stat().st_size
            else:
                size_bytes = sum(f.stat().st_size for f in data_path.rglob('*') if f.is_file())

            # Create version info
            version = DataVersion(
                path=str(data_path),
                dvc_file=dvc_file,
                version_hash=self._get_file_hash(str(data_path)),
                size_bytes=size_bytes,
                created_at=datetime.now().isoformat()
            )

            # Commit to git
            self._run_command(["git", "add", dvc_file])
            commit_msg = f"Add dataset: {data_path.name}"
            if description:
                commit_msg += f" - {description}"
            self._run_command(["git", "commit", "-m", commit_msg])

            logger.info(f"Added dataset to DVC: {data_path}")
            return version

        except Exception as e:
            logger.error(f"Failed to add dataset: {e}")
            raise

    def create_model_snapshot(self,
                            model_artifacts: dict[str, str],
                            version_tag: str,
                            performance_metrics: dict[str, float],
                            description: str = "") -> ModelSnapshot:
        """
        Create versioned snapshot of model artifacts.

        Args:
            model_artifacts: Dictionary of artifact_name -> file_path
            version_tag: Version tag (e.g., "v1.2.3", "embedding_v2")
            performance_metrics: Performance metrics for this version
            description: Human-readable description

        Returns:
            ModelSnapshot information
        """
        try:
            snapshot_info = ModelSnapshot(
                version_tag=version_tag,
                timestamp=datetime.now().isoformat(),
                artifacts={},
                performance_metrics=performance_metrics,
                description=description
            )

            # Add each artifact to DVC
            for artifact_name, artifact_path in model_artifacts.items():
                artifact_path = Path(artifact_path)

                if not artifact_path.exists():
                    logger.warning(f"Artifact not found: {artifact_path}")
                    continue

                # Add to DVC
                self._run_command(["dvc", "add", str(artifact_path)])

                snapshot_info.artifacts[artifact_name] = {
                    'path': str(artifact_path),
                    'dvc_file': f"{artifact_path}.dvc",
                    'hash': self._get_file_hash(str(artifact_path))
                }

            # Save snapshot metadata
            snapshot_file = self.snapshots_dir / f"{version_tag}_snapshot.json"
            with open(snapshot_file, 'w') as f:
                json.dump({
                    'version_tag': snapshot_info.version_tag,
                    'timestamp': snapshot_info.timestamp,
                    'artifacts': snapshot_info.artifacts,
                    'performance_metrics': snapshot_info.performance_metrics,
                    'description': snapshot_info.description
                }, f, indent=2)

            # Commit everything to git
            dvc_files = [f"{path}.dvc" for path in model_artifacts.values()]
            self._run_command(["git", "add"] + dvc_files + [str(snapshot_file)])

            commit_msg = f"Model snapshot {version_tag}: {description}"
            self._run_command(["git", "commit", "-m", commit_msg])

            # Get git commit hash
            result = self._run_command(["git", "rev-parse", "HEAD"])
            snapshot_info.git_commit = result.stdout.strip()

            # Create git tag
            self._run_command(["git", "tag", f"model-{version_tag}"])

            logger.info(f"Created model snapshot: {version_tag}")
            return snapshot_info

        except Exception as e:
            logger.error(f"Failed to create model snapshot: {e}")
            raise

    def rollback_model(self, version_tag: str) -> bool:
        """
        Rollback to a previous model version.

        Args:
            version_tag: Version tag to rollback to

        Returns:
            True if rollback successful
        """
        try:
            # Find snapshot file
            snapshot_file = self.snapshots_dir / f"{version_tag}_snapshot.json"

            if not snapshot_file.exists():
                raise FileNotFoundError(f"Snapshot not found: {version_tag}")

            # Load snapshot info
            with open(snapshot_file) as f:
                snapshot_data = json.load(f)

            # Checkout git tag
            self._run_command(["git", "checkout", f"model-{version_tag}"])

            # Checkout DVC files
            for artifact_info in snapshot_data['artifacts'].values():
                dvc_file = artifact_info['dvc_file']
                self._run_command(["dvc", "checkout", dvc_file])

            logger.info(f"Rolled back to model version: {version_tag}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback model: {e}")
            return False

    def list_model_versions(self) -> list[ModelSnapshot]:
        """
        List all available model versions.

        Returns:
            List of ModelSnapshot objects
        """
        versions = []

        try:
            for snapshot_file in self.snapshots_dir.glob("*_snapshot.json"):
                with open(snapshot_file) as f:
                    data = json.load(f)

                versions.append(ModelSnapshot(
                    version_tag=data['version_tag'],
                    timestamp=data['timestamp'],
                    artifacts=data['artifacts'],
                    performance_metrics=data['performance_metrics'],
                    description=data['description'],
                    git_commit=data.get('git_commit')
                ))

            # Sort by timestamp (newest first)
            versions.sort(key=lambda x: x.timestamp, reverse=True)

        except Exception as e:
            logger.error(f"Failed to list model versions: {e}")

        return versions

    def compare_model_performance(self, version1: str, version2: str) -> dict[str, Any]:
        """
        Compare performance metrics between two model versions.

        Args:
            version1: First version tag
            version2: Second version tag

        Returns:
            Comparison results
        """
        try:
            versions = self.list_model_versions()
            version_dict = {v.version_tag: v for v in versions}

            if version1 not in version_dict:
                raise ValueError(f"Version not found: {version1}")
            if version2 not in version_dict:
                raise ValueError(f"Version not found: {version2}")

            v1_metrics = version_dict[version1].performance_metrics
            v2_metrics = version_dict[version2].performance_metrics

            comparison = {
                'version1': version1,
                'version2': version2,
                'metrics_comparison': {},
                'better_version': {},
                'summary': {}
            }

            # Compare each metric
            for metric_name in set(v1_metrics.keys()) | set(v2_metrics.keys()):
                v1_val = v1_metrics.get(metric_name)
                v2_val = v2_metrics.get(metric_name)

                if v1_val is not None and v2_val is not None:
                    diff = v2_val - v1_val
                    percent_change = (diff / v1_val) * 100 if v1_val != 0 else 0

                    comparison['metrics_comparison'][metric_name] = {
                        f'{version1}_value': v1_val,
                        f'{version2}_value': v2_val,
                        'absolute_difference': diff,
                        'percent_change': percent_change
                    }

                    # Determine which is better (higher is better for most metrics)
                    comparison['better_version'][metric_name] = version2 if v2_val > v1_val else version1

            return comparison

        except Exception as e:
            logger.error(f"Failed to compare model performance: {e}")
            raise

    def setup_ab_testing(self,
                        baseline_version: str,
                        challenger_version: str,
                        traffic_split: float = 0.1) -> dict[str, str]:
        """
        Setup A/B testing between two model versions.

        Args:
            baseline_version: Current production version
            challenger_version: New version to test
            traffic_split: Fraction of traffic to send to challenger (0.0-1.0)

        Returns:
            A/B testing configuration
        """
        try:
            ab_config = {
                'baseline_version': baseline_version,
                'challenger_version': challenger_version,
                'traffic_split': traffic_split,
                'start_time': datetime.now().isoformat(),
                'status': 'active'
            }

            # Save A/B testing config
            ab_config_file = self.snapshots_dir / "ab_testing_config.json"
            with open(ab_config_file, 'w') as f:
                json.dump(ab_config, f, indent=2)

            # Commit config
            self._run_command(["git", "add", str(ab_config_file)])
            self._run_command(["git", "commit", "-m", f"Start A/B test: {baseline_version} vs {challenger_version}"])

            logger.info(f"A/B testing setup: {baseline_version} vs {challenger_version} ({traffic_split:.1%} to challenger)")
            return ab_config

        except Exception as e:
            logger.error(f"Failed to setup A/B testing: {e}")
            raise

    def _get_file_hash(self, file_path: str) -> str:
        """Get file hash for versioning."""
        try:
            self._run_command(["dvc", "status", file_path])
            # Extract hash from DVC status output
            # This is a simplified version - in practice you'd parse the DVC metadata
            import hashlib
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except:
            return "unknown"

    def get_current_model_info(self) -> dict[str, Any]:
        """Get information about currently active model."""
        try:
            # Get current git branch/commit
            branch_result = self._run_command(["git", "branch", "--show-current"])
            commit_result = self._run_command(["git", "rev-parse", "HEAD"])

            current_info = {
                'git_branch': branch_result.stdout.strip(),
                'git_commit': commit_result.stdout.strip(),
                'timestamp': datetime.now().isoformat()
            }

            # Try to find associated model snapshot
            versions = self.list_model_versions()
            for version in versions:
                if version.git_commit == current_info['git_commit']:
                    current_info['model_version'] = version.version_tag
                    current_info['performance_metrics'] = version.performance_metrics
                    break

            return current_info

        except Exception as e:
            logger.error(f"Failed to get current model info: {e}")
            return {}

    def cleanup_old_versions(self, keep_last_n: int = 10) -> list[str]:
        """
        Cleanup old model versions, keeping only the most recent N.

        Args:
            keep_last_n: Number of versions to keep

        Returns:
            List of removed version tags
        """
        try:
            versions = self.list_model_versions()

            if len(versions) <= keep_last_n:
                logger.info("No versions to cleanup")
                return []

            versions_to_remove = versions[keep_last_n:]
            removed_tags = []

            for version in versions_to_remove:
                try:
                    # Remove snapshot file
                    snapshot_file = self.snapshots_dir / f"{version.version_tag}_snapshot.json"
                    if snapshot_file.exists():
                        snapshot_file.unlink()

                    # Remove git tag
                    self._run_command(["git", "tag", "-d", f"model-{version.version_tag}"])

                    removed_tags.append(version.version_tag)
                    logger.info(f"Removed old version: {version.version_tag}")

                except Exception as e:
                    logger.warning(f"Failed to remove version {version.version_tag}: {e}")

            if removed_tags:
                # Commit cleanup
                self._run_command(["git", "add", "-A"])
                self._run_command(["git", "commit", "-m", f"Cleanup old model versions: {removed_tags}"])

            return removed_tags

        except Exception as e:
            logger.error(f"Failed to cleanup old versions: {e}")
            return []
