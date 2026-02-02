"""
Recent files manager - tracks and persists recently opened files.
"""

from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, pyqtSignal


class RecentFilesManager(QObject):
    """Manages a list of recently opened files."""

    # Signal emitted when the recent files list changes
    files_changed = pyqtSignal()

    MAX_RECENT_FILES = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MyNotion", "Editor")
        self._recent_files: list[str] = []
        self._load()

    def _load(self):
        """Load recent files from settings."""
        files = self.settings.value("recent_files", [])
        if files:
            # Filter out files that no longer exist
            self._recent_files = [f for f in files if Path(f).exists()]
            # Save back the cleaned list
            self._save()
        else:
            self._recent_files = []

    def _save(self):
        """Save recent files to settings."""
        self.settings.setValue("recent_files", self._recent_files)

    def add_file(self, filepath: str):
        """Add a file to the recent files list."""
        # Normalize the path
        filepath = str(Path(filepath).resolve())

        # Remove if already in list (will be re-added at top)
        if filepath in self._recent_files:
            self._recent_files.remove(filepath)

        # Add to the beginning
        self._recent_files.insert(0, filepath)

        # Trim to max size
        self._recent_files = self._recent_files[: self.MAX_RECENT_FILES]

        self._save()
        self.files_changed.emit()

    def remove_file(self, filepath: str):
        """Remove a file from the recent files list."""
        filepath = str(Path(filepath).resolve())
        if filepath in self._recent_files:
            self._recent_files.remove(filepath)
            self._save()
            self.files_changed.emit()

    def clear(self):
        """Clear all recent files."""
        self._recent_files = []
        self._save()
        self.files_changed.emit()

    def get_files(self) -> list[str]:
        """Get the list of recent files."""
        return self._recent_files.copy()

    def get_display_name(self, filepath: str) -> str:
        """Get a display-friendly name for the file."""
        path = Path(filepath)
        # Show filename and parent folder for context
        if path.parent.name:
            return f"{path.name}  —  {path.parent}"
        return path.name
