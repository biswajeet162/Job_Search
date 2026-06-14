import json
from pathlib import Path
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileService:
    """Low-level file I/O operations."""

    def ensure_directory(self, directory: Path) -> Path:
        """Create directory if it does not exist."""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_json(self, file_path: Path, data: dict[str, Any] | list[Any]) -> Path:
        """Write JSON data to disk with UTF-8 encoding."""
        self.ensure_directory(file_path.parent)
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        logger.debug("Wrote JSON file: %s", file_path)
        return file_path

    def read_json(self, file_path: Path) -> dict[str, Any] | list[Any]:
        """Read JSON data from disk."""
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def list_json_files(self, directory: Path, limit: int | None = None) -> list[Path]:
        """List JSON files in directory sorted by name (newest last)."""
        if not directory.exists():
            return []
        files = sorted(directory.glob("*.json"))
        if limit is not None:
            return files[-limit:]
        return files

    def list_date_directories(self, base_dir: Path) -> list[Path]:
        """List date subdirectories sorted chronologically."""
        if not base_dir.exists():
            return []
        return sorted(
            [path for path in base_dir.iterdir() if path.is_dir()],
            key=lambda p: p.name,
        )
