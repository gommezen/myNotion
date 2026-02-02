"""
MyNotion - Lightweight Text and Code Editor
Entry point for the application.
"""

import os
import sys

# High DPI scaling for Windows
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

from app import run_app

if __name__ == "__main__":
    sys.exit(run_app())
