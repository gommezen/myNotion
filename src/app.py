"""
Application setup and event loop configuration.
"""

import asyncio
import sys

from PyQt6.QtCore import QSettings, QtMsgType, qInstallMessageHandler
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

from ui.main_window import MainWindow

# Store original message handler
_original_handler = None


def qt_message_handler(msg_type: QtMsgType, context, message: str):
    """Custom Qt message handler to filter font warnings."""
    # Filter out the font point size warning (cosmetic, doesn't affect functionality)
    if "QFont::setPointSize" in message and "Point size <= 0" in message:
        return  # Suppress this specific warning
    # For all other messages, print them normally
    if msg_type == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif msg_type == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif msg_type == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")


def fix_corrupted_settings():
    """Fix any corrupted settings values."""
    settings = QSettings("MyNotion", "Editor")

    # Fix font_size if corrupted
    font_size = settings.value("font_size")
    if font_size is not None:
        try:
            size = int(font_size)
            if size <= 0 or size > 100:
                settings.setValue("font_size", 12)
        except (ValueError, TypeError):
            settings.setValue("font_size", 12)


def setup_default_font(app: QApplication):
    """Set a valid default application font to prevent -1 point size issues."""
    # Create a new font with explicit family and size (more reliable than systemFont)
    font = QFont("Consolas", 12)  # Consolas is available on all Windows systems

    # Fallback to system font if Consolas doesn't work
    if font.family() != "Consolas":
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if font.pointSize() <= 0:
            font.setPointSize(12)

    # Set as application default
    app.setFont(font)


def run_app() -> int:
    """Initialize and run the application with async support."""
    # Install custom message handler to filter font warnings
    qInstallMessageHandler(qt_message_handler)

    app = QApplication(sys.argv)
    app.setApplicationName("MyNotion")
    app.setOrganizationName("MyNotion")

    # Set up a valid default font before any widgets are created
    setup_default_font(app)

    # Fix any corrupted settings
    fix_corrupted_settings()

    # Set up async event loop with Qt integration
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    app.processEvents()  # Force stylesheet cascade before first paint
    window.show()

    # Run event loop
    with loop:
        return loop.run_forever()
