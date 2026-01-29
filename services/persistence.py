"""
Persistence module for VC Thesis Sprint application.
Handles JSON-based serialization/deserialization of sprints and companies.
"""
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
import logging

from models import ThesisSprint, Company

logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages JSON-based persistence for sprints and companies."""

    def __init__(self, data_dir: str = "./data"):
        """
        Initialize persistence manager.

        Args:
            data_dir: Directory path for storing JSON files
        """
        self.data_dir = Path(data_dir)
        self.sprints_file = self.data_dir / "sprints.json"
        self.companies_file = self.data_dir / "companies.json"
        self.initialize_storage()

    def initialize_storage(self) -> None:
        """Create data directory if it doesn't exist."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Data directory initialized at {self.data_dir}")
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise

    def save_to_disk(
        self,
        sprints: Dict[str, ThesisSprint],
        companies: Dict[str, Company]
    ) -> bool:
        """
        Save sprints and companies to JSON files with atomic writes.

        Args:
            sprints: Dictionary of sprint_id -> ThesisSprint
            companies: Dictionary of company_id -> Company

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Serialize sprints
            sprints_data = {
                sprint_id: sprint.model_dump(mode='json')
                for sprint_id, sprint in sprints.items()
            }

            # Serialize companies
            companies_data = {
                company_id: company.model_dump(mode='json')
                for company_id, company in companies.items()
            }

            # Atomic write for sprints
            self._atomic_write(self.sprints_file, sprints_data)

            # Atomic write for companies
            self._atomic_write(self.companies_file, companies_data)

            logger.info(
                f"Saved {len(sprints)} sprints and {len(companies)} companies"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            return False

    def load_from_disk(self) -> Optional[tuple[Dict[str, ThesisSprint], Dict[str, Company]]]:
        """
        Load sprints and companies from JSON files.

        Returns:
            Tuple of (sprints_dict, companies_dict) or None if files don't exist
        """
        # Check if files exist
        if not self.sprints_file.exists() or not self.companies_file.exists():
            logger.info("No existing data files found")
            return None

        try:
            # Load sprints
            sprints_data = self._load_json_with_backup(self.sprints_file)
            if sprints_data is None:
                logger.warning("Failed to load sprints, returning None")
                return None

            sprints = {
                sprint_id: ThesisSprint.model_validate(sprint_dict)
                for sprint_id, sprint_dict in sprints_data.items()
            }

            # Load companies
            companies_data = self._load_json_with_backup(self.companies_file)
            if companies_data is None:
                logger.warning("Failed to load companies, returning None")
                return None

            companies = {
                company_id: Company.model_validate(company_dict)
                for company_id, company_dict in companies_data.items()
            }

            logger.info(
                f"Loaded {len(sprints)} sprints and {len(companies)} companies"
            )
            return sprints, companies

        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return None

    def _atomic_write(self, file_path: Path, data: dict) -> None:
        """
        Write JSON data atomically using temp file + rename.
        Also creates a backup of the previous file.

        Args:
            file_path: Target file path
            data: Dictionary to serialize as JSON
        """
        # Create backup of existing file
        if file_path.exists():
            backup_path = Path(str(file_path) + ".backup")
            shutil.copy2(file_path, backup_path)

        # Write to temporary file
        temp_path = Path(str(file_path) + ".tmp")
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.replace(file_path)

    def _load_json_with_backup(self, file_path: Path) -> Optional[dict]:
        """
        Load JSON file with fallback to backup if primary is corrupt.

        Args:
            file_path: Path to JSON file

        Returns:
            Loaded dictionary or None if both primary and backup fail
        """
        # Try primary file
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupt JSON in {file_path}: {e}")
            # Try backup
            backup_path = Path(str(file_path) + ".backup")
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as f:
                        logger.info(f"Loaded from backup: {backup_path}")
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Backup also corrupt: {e}")
            return None
        except FileNotFoundError:
            logger.info(f"File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path}: {e}")
            return None


# Global singleton instance
_persistence_manager: Optional[PersistenceManager] = None


def get_persistence_manager(data_dir: str = "./data") -> PersistenceManager:
    """
    Get or create the global PersistenceManager instance.

    Args:
        data_dir: Directory path for storing JSON files

    Returns:
        PersistenceManager instance
    """
    global _persistence_manager
    if _persistence_manager is None:
        _persistence_manager = PersistenceManager(data_dir)
    return _persistence_manager
