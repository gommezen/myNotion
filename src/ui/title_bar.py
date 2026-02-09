"""
Title bar controller — custom frameless window chrome with drag, resize, and snapping.

Manages the custom title bar widget, window control buttons (min/max/close),
resize grips, DWM title bar colors, and Win+Arrow snapping.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class TitleBarController:
    """Manages the custom frameless title bar, resize grips, and window snapping.

    Not a QObject — a plain helper owned by MainWindow.  MainWindow delegates
    ``eventFilter``, ``keyPressEvent``, and ``resizeEvent`` calls here.
    """

    # Edge → cursor mapping for resize grips
    _EDGE_CURSORS = {
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    }

    def __init__(self, window: QMainWindow) -> None:
        self._win = window

        # Drag / resize state
        self._drag_pos: QPoint | None = None
        self._resize_edge = ""
        self._resize_origin = QPoint()
        self._resize_geo = window.geometry()

        # Widgets created in setup()
        self._title_bar: QWidget | None = None
        self._title_text_label: QLabel | None = None
        self._title_icon_label: QLabel | None = None
        self._min_btn: QToolButton | None = None
        self._max_btn: QToolButton | None = None
        self._close_btn: QToolButton | None = None
        self._header_widget: QWidget | None = None
        self._resize_grips: dict[str, QWidget] = {}

    # ─── Setup ──────────────────────────────────────────────────────

    def setup_frameless(self) -> None:
        """Make the window frameless and enable native Win+Arrow snapping."""
        self._win.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._enable_native_snapping()

        # Set taskbar icon
        icon_path = self._get_resource_path("mynotion.ico")
        if icon_path.exists():
            self._win.setWindowIcon(QIcon(str(icon_path)))

    def create_title_bar(self, header_vlayout: QVBoxLayout) -> None:
        """Build the custom title bar row and add it to *header_vlayout*."""
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(26)
        tb_layout = QHBoxLayout(self._title_bar)
        tb_layout.setContentsMargins(4, 2, 2, 2)
        tb_layout.setSpacing(4)

        # App icon (16x16)
        self._title_icon_label = QLabel()
        self._title_icon_label.setFixedSize(16, 16)
        self._title_icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_path = self._get_resource_path("mynotion.ico")
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            self._title_icon_label.setPixmap(icon.pixmap(16, 16))
        tb_layout.addWidget(self._title_icon_label)

        # Title text
        self._title_text_label = QLabel("MyNotion")
        self._title_text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        tb_layout.addWidget(self._title_text_label)
        tb_layout.addStretch()

        # Window control buttons: minimize, maximize, close
        self._min_btn = QToolButton()
        self._min_btn.setText("\u2500")
        self._min_btn.setFixedSize(22, 18)
        self._min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._min_btn.clicked.connect(self._win.showMinimized)
        tb_layout.addWidget(self._min_btn)

        self._max_btn = QToolButton()
        self._max_btn.setText("\u25a1")
        self._max_btn.setFixedSize(22, 18)
        self._max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._max_btn.clicked.connect(self._toggle_maximize)
        tb_layout.addWidget(self._max_btn)

        self._close_btn = QToolButton()
        self._close_btn.setText("\u00d7")
        self._close_btn.setFixedSize(22, 18)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._win.close)
        tb_layout.addWidget(self._close_btn)

        header_vlayout.addWidget(self._title_bar)

        # Install event filter for title-bar dragging
        self._title_bar.installEventFilter(self._win)

        # Expose widgets on the window so ThemeEngine can style them
        self._win._custom_title_bar = self._title_bar  # type: ignore[attr-defined]
        self._win._title_text_label = self._title_text_label  # type: ignore[attr-defined]
        self._win._title_icon_label = self._title_icon_label  # type: ignore[attr-defined]
        self._win._min_btn = self._min_btn  # type: ignore[attr-defined]
        self._win._max_btn = self._max_btn  # type: ignore[attr-defined]
        self._win._close_btn = self._close_btn  # type: ignore[attr-defined]

    def setup_resize_grips(self) -> None:
        """Create invisible overlay widgets at window edges for resize."""
        self._resize_grips = {}
        for edge, cursor in self._EDGE_CURSORS.items():
            grip = QWidget(self._win)
            grip.setCursor(cursor)
            grip.setStyleSheet("background: transparent;")
            grip.setProperty("resize_edge", edge)
            grip.installEventFilter(self._win)
            self._resize_grips[edge] = grip
        self.position_resize_grips()

    def position_resize_grips(self) -> None:
        """Position resize grips at window edges and corners."""
        g = 6
        w, h = self._win.width(), self._win.height()
        gr = self._resize_grips
        if not gr:
            return
        gr["top"].setGeometry(g, 0, w - 2 * g, g)
        gr["bottom"].setGeometry(g, h - g, w - 2 * g, g)
        gr["left"].setGeometry(0, g, g, h - 2 * g)
        gr["right"].setGeometry(w - g, g, g, h - 2 * g)
        gr["top_left"].setGeometry(0, 0, g, g)
        gr["top_right"].setGeometry(w - g, 0, g, g)
        gr["bottom_left"].setGeometry(0, h - g, g, g)
        gr["bottom_right"].setGeometry(w - g, h - g, g, g)
        for grip in gr.values():
            grip.raise_()

    # ─── Window title ───────────────────────────────────────────────

    def update_title(self, title: str) -> None:
        """Update the title bar label text."""
        if self._title_text_label:
            self._title_text_label.setText(title)

    # ─── DWM colors (Windows 11) ───────────────────────────────────

    @staticmethod
    def apply_title_bar_color(window: QMainWindow, hex_color: str) -> None:
        """Set the Windows title bar color using the DWM API."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(window.winId())
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            color = ctypes.c_int(r | (g << 8) | (b << 16))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 35, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass

    @staticmethod
    def apply_title_bar_text_color(window: QMainWindow, hex_color: str) -> None:
        """Set the Windows title bar text color using the DWM API."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(window.winId())
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            color = ctypes.c_int(r | (g << 8) | (b << 16))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 36, ctypes.byref(color), ctypes.sizeof(color)
            )
        except Exception:
            pass

    # ─── Event delegation ───────────────────────────────────────────

    def handle_event_filter(self, obj: object, event: QEvent) -> bool:
        """Handle title-bar drag and resize-grip events.

        Returns True if the event was consumed, False to let the caller
        fall through to ``super().eventFilter()``.
        """
        # ── Title bar dragging ──
        if self._title_bar is not None and obj == self._title_bar:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._drag_pos is not None:
                    if self._win.isMaximized():
                        ratio = event.position().x() / self._win.width()
                        self._win.showNormal()
                        self._max_btn.setText("\u25a1")
                        new_x = int(event.globalPosition().x() - self._win.width() * ratio)
                        new_y = int(event.globalPosition().y() - 13)
                        self._win.move(new_x, new_y)
                        self._drag_pos = event.globalPosition().toPoint()
                    else:
                        delta = event.globalPosition().toPoint() - self._drag_pos
                        self._win.move(self._win.pos() + delta)
                        self._drag_pos = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_pos = None
                return True
            elif (
                event.type() == QEvent.Type.MouseButtonDblClick
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._toggle_maximize()
                return True

        # ── Resize grip handling ──
        edge = obj.property("resize_edge") if hasattr(obj, "property") else None
        if edge and not self._win.isMaximized():
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._resize_edge = edge
                self._resize_origin = event.globalPosition().toPoint()
                self._resize_geo = self._win.geometry()
                return True
            if event.type() == QEvent.Type.MouseMove and self._resize_edge:
                delta = event.globalPosition().toPoint() - self._resize_origin
                geo = self._resize_geo
                new_geo = geo.__class__(geo)
                if "left" in self._resize_edge:
                    new_geo.setLeft(geo.left() + delta.x())
                if "right" in self._resize_edge:
                    new_geo.setRight(geo.right() + delta.x())
                if "top" in self._resize_edge:
                    new_geo.setTop(geo.top() + delta.y())
                if "bottom" in self._resize_edge:
                    new_geo.setBottom(geo.bottom() + delta.y())
                if (
                    new_geo.width() >= self._win.minimumWidth()
                    and new_geo.height() >= self._win.minimumHeight()
                ):
                    self._win.setGeometry(new_geo)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._resize_edge = ""
                return True

        return False

    def handle_key_press(self, event) -> bool:
        """Handle Win+Arrow window snapping.

        Returns True if the event was consumed.
        """
        if event.modifiers() != Qt.KeyboardModifier.MetaModifier:
            return False

        screen = self._win.screen().availableGeometry()
        key = event.key()

        if key == Qt.Key.Key_Left:
            self._win.showNormal()
            self._max_btn.setText("\u25a1")
            self._win.setGeometry(screen.x(), screen.y(), screen.width() // 2, screen.height())
            return True
        if key == Qt.Key.Key_Right:
            self._win.showNormal()
            self._max_btn.setText("\u25a1")
            self._win.setGeometry(
                screen.x() + screen.width() // 2,
                screen.y(),
                screen.width() // 2,
                screen.height(),
            )
            return True
        if key == Qt.Key.Key_Up:
            self._win.showMaximized()
            self._max_btn.setText("\u2750")
            return True
        if key == Qt.Key.Key_Down:
            if self._win.isMaximized():
                self._win.showNormal()
                self._max_btn.setText("\u25a1")
            else:
                self._win.showMinimized()
            return True

        return False

    # ─── Private helpers ────────────────────────────────────────────

    def _toggle_maximize(self) -> None:
        """Toggle between maximized and normal window state."""
        if self._win.isMaximized():
            self._win.showNormal()
            self._max_btn.setText("\u25a1")
        else:
            self._win.showMaximized()
            self._max_btn.setText("\u2750")

    def _enable_native_snapping(self) -> None:
        """Add WS_THICKFRAME to enable native Win+Arrow snapping on Windows."""
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self._win.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -16)
            style |= 0x00040000 | 0x00010000 | 0x00020000
            ctypes.windll.user32.SetWindowLongW(hwnd, -16, style)
        except Exception:
            pass

    @staticmethod
    def _get_resource_path(filename: str) -> Path:
        """Get path to a resource file, supporting both dev and PyInstaller."""
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent.parent
        return base_path / "resources" / filename
