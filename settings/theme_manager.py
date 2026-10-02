import os
import sys

from PyQt5.QtCore import QObject, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication

from .settings_manager import WWSettingsManager


class ThemeManager(QObject):
    """
    A simple manager for predefined themes.

    Provides methods to:
      - List available themes.
      - Retrieve a stylesheet for a given theme.
      - Apply a theme to a specific widget or the entire application.
      - Generate tinted SVG icons using QSvgRenderer.
    """

    # Signal emitted when theme changes
    themeChanged = pyqtSignal(str)

    _instance = None
    _icon_cache = {}  # Cache: (file_path, tint_color) -> QIcon

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize the QObject part
            cls._instance.__init_signals()
        return cls._instance

    def __init_signals(self):
        # This ensures the QObject is properly initialized
        super().__init__()

    # CSS themes with glassmorphism and neumorphism effects
    THEMES = {
        "Juvion": """
            QMainWindow, QWidget {
                background-color: #fbf9f6;
                color: #1b1c1a;
                font-family: "Segoe UI", "Inter", Arial, sans-serif;
                font-size: 13px;
            }
            QToolBar, QStatusBar {
                background-color: #f5f3f0;
                border: none;
                border-bottom: 1px solid #e4e2df;
                spacing: 5px;
                padding: 7px 10px;
            }
            QStatusBar {
                border-top: 1px solid #e4e2df;
                border-bottom: none;
                color: #645d59;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 7px;
            }
            QToolButton:hover, QToolButton:checked {
                background-color: #ebe0dc;
            }
            QToolButton:checked {
                border: 1px solid #e0bfbf;
            }
            QPushButton {
                background-color: #efeeeb;
                color: #1b1c1a;
                border: 1px solid #e4e2df;
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e4e2df;
                border-color: #cfc9c5;
            }
            QPushButton:pressed {
                background-color: #dcd5d0;
            }
            QPushButton[primary="true"] {
                background-color: #7b001f;
                color: #ffffff;
                border-color: #7b001f;
            }
            QPushButton[primary="true"]:hover {
                background-color: #9e1b32;
                border-color: #9e1b32;
            }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
                background-color: #ffffff;
                color: #1b1c1a;
                border: 1px solid #e4e2df;
                border-radius: 6px;
                padding: 7px 9px;
                selection-background-color: #ffdada;
                selection-color: #40000c;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #7b001f;
            }
            QTextEdit#ManuscriptEditor {
                background-color: #ffffff;
                color: #2c2523;
                border: 1px solid #e4e2df;
                border-radius: 10px;
                font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
                font-size: 15pt;
                line-height: 1.7;
                padding: 42px 56px;
            }
            QTreeView, QTreeWidget {
                background-color: #f5f3f0;
                color: #1b1c1a;
                border: none;
                outline: 0;
            }
            QTreeView::item, QTreeWidget::item {
                padding: 7px 5px;
                border-radius: 5px;
            }
            QTreeView::item:hover, QTreeWidget::item:hover {
                background-color: #ebe0dc;
            }
            QTreeView::item:selected, QTreeWidget::item:selected {
                background-color: #ffdada;
                color: #7b001f;
            }
            QHeaderView::section {
                background-color: #f5f3f0;
                color: #645d59;
                border: none;
                border-bottom: 1px solid #e4e2df;
                padding: 8px;
                font-weight: 700;
            }
            QSplitter::handle {
                background-color: #e4e2df;
                width: 1px;
                height: 1px;
            }
            QSplitter::handle:hover {
                background-color: #7b001f;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cfc9c5;
                border-radius: 5px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover {
                background: #8c7071;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QMenu {
                background-color: #ffffff;
                color: #1b1c1a;
                border: 1px solid #e4e2df;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 7px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #ebe0dc;
                color: #7b001f;
            }
            QLabel#headerLabel {
                color: #1b1c1a;
                font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
                font-size: 25px;
                font-weight: 700;
            }
            QWidget#StudioHeader {
                background-color: #f5f3f0;
                border-bottom: 1px solid #e4e2df;
            }
            QLabel#StudioProjectTitle {
                color: #1b1c1a;
                font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
                font-size: 19px;
                font-weight: 700;
            }
            QLabel#StudioProjectMeta {
                color: #645d59;
                font-size: 11px;
            }
            QWidget#BookDetailsPanel {
                background-color: #f5f3f0;
            }
            QLabel#PanelTitle {
                color: #1b1c1a;
                font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#PanelDescription, QLabel#FieldHint {
                color: #645d59;
            }
            QLabel#BookCoverPreview {
                background-color: #ffffff;
                color: #645d59;
                border: 1px solid #e4e2df;
                border-radius: 8px;
            }
        """,
                "Standard": """
            QTreeWidgetItem[is-category="true"] {
                background-color: #e0e0e0; /* Fallback; will be overridden programmatically */
                font-weight: bold;
            }        
        """,
        "Night Mode": """
            /* Night Mode styling */
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: Arial, "Helvetica Neue", Verdana;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #424242;
            font-weight: bold;
            }
            QLineEdit, QTextEdit {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: #333;
                color: #ffffff;
                border: 2px solid #ffffff;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QTreeView, QTreeWidget {
                background-color: #3c3f41;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3f41;
                color: #ffffff;
                padding: 4px;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #3c3f41;
                color: #ffffff;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #555;
            }
            QToolBar {
                background-color: #2b2b2b; /* Match QWidget background */
                border: none;
                padding: 2px;
            }
            QToolBar::separator {
                background: #555;
                width: 1px;
            }
            QToolButton {
                background-color: #2b2b2b; /* Match toolbar background */
                border: none;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #444; /* Match QPushButton hover */
            }
            QToolButton:pressed {
                background-color: #555;
            }
        """,
        "Solarized Dark": """
            QWidget {
                background-color: #002b36;
                color: #839496;
                font-family: Arial, "Helvetica Neue", Verdana;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #073642;
            font-weight: bold;
        }
            QLineEdit, QTextEdit {
                background-color: #073642;
                color: #93a1a1;
                border: 1px solid #586e75;
            }
            QPushButton {
                background-color: #586e75;
                color: #fdf6e3;
                border: 2px solid #fdf6e3;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #657b83;
            }
            QTreeView, QTreeWidget {
                background-color: #073642;
                color: #839496;
            }
            QHeaderView::section {
                background-color: #073642;
                color: #93a1a1;
                padding: 4px;
            }
            QTabBar::tab {
                background: #073642;
                color: #839496;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #586e75;
            }
            QToolBar {
                background-color: #002b36; /* Match QWidget background */
                border: none;
                padding: 2px;
            }
            QToolBar::separator {
                background: #555;
                width: 1px;
            }
            QToolButton {
                background-color: #002b36; /* Match toolbar background */
                border: none;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #657b83; /* Match QPushButton hover */
            }
            QToolButton:pressed {
                background-color: #586e75;
            }
        """,
        "Paper White": """
            QWidget {
                background-color: #f9f9f9;
                color: #333;
                font-family: "Georgia", serif;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #f7f7f5;
            font-weight: bold;
            }

            QLineEdit, QTextEdit {
                background-color: #ffffff;
                color: #000;
                border: 1px solid #ccc;
            }
            QPushButton {
                background-color: #f1f1f1;
                color: #333;
                border: 2px solid #333;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e1e1e1;
            }
            QTreeView, QTreeWidget {
                background-color: #f9f9f9;
                color: #333;
            }
            QHeaderView::section {
                background-color: #e1e1e1;
                color: #333;
                padding: 4px;
            }
            QTabBar::tab {
                background: #f1f1f1;
                color: #333;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #ddd;
            }
        """,
        "Ocean Breeze": """
            QWidget {
                background-color: #e0f7fa;
                color: #0277bd;
                font-family: "Verdana", "Helvetica Neue", Arial;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #d6f5f9;
            font-weight: bold;
            } 
            QLineEdit, QTextEdit {
                background-color: #b2ebf2;
                color: #004d40;
                border: 1px solid #0288d1;
            }
            QPushButton {
                background-color: #4dd0e1;
                color: #004d40;
                border: 2px solid #004d40;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #26c6da;
            }
            QTreeView, QTreeWidget {
                background-color: #b2ebf2;
                color: #004d40;
            }
            QHeaderView::section {
                background-color: #4dd0e1;
                color: #004d40;
                padding: 4px;
            }
            QTabBar::tab {
                background: #b2ebf2;
                color: #0277bd;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #4dd0e1;
            }
        """,
        "Sepia": """
            QWidget {
                background-color: #f4ecd8;
                color: #5a4630;
                font-family: "Times New Roman", serif;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #f9f2e5;
            font-weight: bold;
        }
            QLineEdit, QTextEdit {
                background-color: #f8f1e4;
                color: #3a2c1f;
                border: 1px solid #a67c52;
            }
            QPushButton {
                background-color: #d8c3a5;
                color: #3a2c1f;
                border: 2px solid #3a2c1f;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c4a484;
            }
            QTreeView, QTreeWidget {
                background-color: #f4ecd8;
                color: #5a4630;
            }
            QHeaderView::section {
                background-color: #d8c3a5;
                color: #5a4630;
                padding: 4px;
            }
            QTabBar::tab {
                background: #d8c3a5;
                color: #5a4630;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #c4a484;
            }
        """,

        "Notion Light": """
            /* Enhanced Notion Light Theme with Accessibility Features */
            QWidget {
                background-color: #ffffff;
                color: #37352f;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, Verdana;
                font-size: 14px;
                line-height: 1.5;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #f7f7f5;
            font-weight: bold;
            }

            /* Main window styling */
            QMainWindow {
                background-color: #ffffff;
            }

            /* Text editing areas */
            QTextEdit, QPlainTextEdit {
                background-color: #ffffff;
                color: #37352f;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 12px;
                font-family: "SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, Verdana;
                font-size: 15px;
                line-height: 1.6;
                selection-background-color: #e7f5ff;
                selection-color: #0066cc;
            }

            QTextEdit:focus {
                border: 2px solid #0066cc;
                outline: none;
            }

            /* Input fields */
            QLineEdit {
                background-color: #f7f7f5;
                color: #37352f;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #0066cc;
                background-color: #ffffff;
                outline: none;
            }

            /* Buttons */
            QPushButton {
                background-color: #f7f7f5;
                color: #37352f;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
                widget-animation-duration: 200;
            }

            QPushButton:hover {
                background-color: #efefef;
                border-color: #d0d0d0;
            }

            QPushButton:pressed {
                background-color: #e0e0e0;
            }

            QPushButton[primary="true"] {
                background-color: #0066cc;
                color: white;
                border: none;
            }

            QPushButton[primary="true"]:hover {
                background-color: #0052a3;
            }

            /* Tree views */
            QTreeView, QTreeWidget {
                background-color: #ffffff;
                color: #37352f;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                alternate-background-color: #f7f7f5;
                outline: 0;
            }

            QTreeView::item, QTreeWidget::item {
                padding: 8px;
                border-radius: 4px;
            }

            QTreeView::item:hover, QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }

            QTreeView::item:selected, QTreeWidget::item:selected {
                background-color: #e7f5ff;
                color: #0066cc;
            }

            /* Headers */
            QHeaderView::section {
                background-color: #f7f7f5;
                color: #37352f;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                font-weight: 600;
                font-size: 13px;
            }

            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
            }

            QTabBar::tab {
                background-color: #f7f7f5;
                color: #6b6b6b;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }

            QTabBar::tab:hover {
                background-color: #efefef;
                color: #37352f;
            }

            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #37352f;
                border: 1px solid #e0e0e0;
                border-bottom: 2px solid #0066cc;
            }

            /* Toolbars */
            QToolBar {
                background-color: #ffffff;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                padding: 8px;
                spacing: 8px;
            }

            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }

            QToolButton:hover {
                background-color: #f0f0f0;
            }

            QToolButton:pressed {
                background-color: #e0e0e0;
            }

            /* Scrollbars */
            QScrollBar:vertical {
                background-color: #f7f7f5;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #d0d0d0;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #b0b0b0;
            }

            QScrollBar:horizontal {
                background-color: #f7f7f5;
                height: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:horizontal {
                background-color: #d0d0d0;
                border-radius: 6px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #b0b0b0;
            }

            /* Menus */
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                padding: 4px;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #f0f0f0;
            }

            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
            }

            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }

            QMenu::item:selected {
                background-color: #e7f5ff;
                color: #0066cc;
            }
        """,

            "Warm Cream": """
            /* Warm Cream — soft paper & sepia ink */
            QWidget {
                background-color: #fdfcfa;
                color: #5a4d41;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, Verdana;
                font-size: 14px;
                line-height: 1.5;
            }
            QTreeWidgetItem[is-category="true"] {
            background-color: #f5e8d0;
            font-weight: bold;
            }

            /* Main window styling */
            QMainWindow {
                background-color: #fdfcfa;
            }

            /* Text editing areas */
            QTextEdit, QPlainTextEdit {
                background-color: #fdfcfa;
                color: #5a4d41;
                border: 1px solid #e8e0d8;
                border-radius: 8px;
                padding: 12px;
                font-family: "SF Pro Text", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, Verdana;
                font-size: 15px;
                line-height: 1.6;
                selection-background-color: #f5e8d0;
                selection-color: #8b5e3c;
            }

            QTextEdit:focus {
                border: 2px solid #c9996b;
                outline: none;
            }

            /* Input fields */
            QLineEdit {
                background-color: #f7f3ef;
                color: #5a4d41;
                border: 1px solid #e8e0d8;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #c9996b;
                background-color: #fdfcfa;
                outline: none;
            }

            /* Buttons */
            QPushButton {
                background-color: #f7f3ef;
                color: #5a4d41;
                border: 1px solid #e8e0d8;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
                widget-animation-duration: 200;
            }

            QPushButton:hover {
                background-color: #ede4da;
                border-color: #d6c7b8;
            }

            QPushButton:pressed {
                background-color: #e8d0b8;
            }

            QPushButton[primary="true"] {
                background-color: #c9996b;
                color: white;
                border: none;
            }

            QPushButton[primary="true"]:hover {
                background-color: #b8885c;
            }

            /* Tree views */
            QTreeView, QTreeWidget {
                background-color: #fdfcfa;
                color: #5a4d41;
                border: 1px solid #e8e0d8;
                border-radius: 8px;
                alternate-background-color: #f7f3ef;
                outline: 0;
            }

            QTreeView::item, QTreeWidget::item {
                padding: 8px;
                border-radius: 4px;
            }

            QTreeView::item:hover, QTreeWidget::item:hover {
                background-color: #f0e8dd;
            }

            QTreeView::item:selected, QTreeWidget::item:selected {
                background-color: #e8d0b8;
                color: #8b5e3c;
            }

            /* Headers */
            QHeaderView::section {
                background-color: #f7f3ef;
                color: #5a4d41;
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #e8e0d8;
                font-weight: 600;
                font-size: 13px;
            }

            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #e8e0d8;
                border-radius: 8px;
                background-color: #fdfcfa;
            }

            QTabBar::tab {
                background-color: #f7f3ef;
                color: #8b8b8b;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }

            QTabBar::tab:hover {
                background-color: #ede4da;
                color: #5a4d41;
            }

            QTabBar::tab:selected {
                background-color: #fdfcfa;
                color: #5a4d41;
                border: 1px solid #e8e0d8;
                border-bottom: 2px solid #c9996b;
            }

            /* Toolbars */
            QToolBar {
                background-color: #fdfcfa;
                border: none;
                border-bottom: 1px solid #e8e0d8;
                padding: 8px;
                spacing: 8px;
            }

            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }

            QToolButton:hover {
                background-color: #f0e8dd;
            }

            QToolButton:pressed {
                background-color: #e8d0b8;
            }

            /* Scrollbars */
            QScrollBar:vertical {
                background-color: #f7f3ef;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #d6c7b8;
                border-radius: 6px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #c9b8a8;
            }

            QScrollBar:horizontal {
                background-color: #f7f3ef;
                height: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:horizontal {
                background-color: #d6c7b8;
                border-radius: 6px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover {
                background-color: #c9b8a8;
            }

            /* Menus */
            QMenuBar {
                background-color: #fdfcfa;
                border-bottom: 1px solid #e8e0d8;
                padding: 4px;
            }

            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }

            QMenuBar::item:selected {
                background-color: #f0e8dd;
            }

            QMenu {
                background-color: #fdfcfa;
                border: 1px solid #e8e0d8;
                border-radius: 8px;
                padding: 4px;
            }

            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }

            QMenu::item:selected {
                background-color: #e8d0b8;
                color: #8b5e3c;
            }
        """,
    }

    JUVION_DARK_THEME = """
        QMainWindow, QWidget {
            background-color: #121212;
            color: #f3efec;
            font-family: "Segoe UI", "Inter", Arial, sans-serif;
            font-size: 13px;
        }
        QToolBar, QStatusBar, QWidget#StudioHeader, QWidget#BookDetailsPanel {
            background-color: #1b1919;
            color: #d8d1cd;
            border: none;
            border-bottom: 1px solid #302c2b;
            spacing: 5px;
            padding: 7px 10px;
        }
        QStatusBar {
            border-top: 1px solid #302c2b;
            border-bottom: none;
        }
        QToolButton {
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 7px;
        }
        QToolButton:hover, QToolButton:checked {
            background-color: #352326;
        }
        QToolButton:checked {
            border: 1px solid #70414a;
        }
        QPushButton {
            background-color: #252222;
            color: #f3efec;
            border: 1px solid #403a38;
            border-radius: 6px;
            padding: 7px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #35302f;
            border-color: #5b504d;
        }
        QPushButton[primary="true"] {
            background-color: #a42c40;
            color: #ffffff;
            border-color: #a42c40;
        }
        QPushButton[primary="true"]:hover {
            background-color: #c54257;
            border-color: #c54257;
        }
        QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {
            background-color: #1b1919;
            color: #f3efec;
            border: 1px solid #403a38;
            border-radius: 6px;
            padding: 7px 9px;
            selection-background-color: #5b2631;
            selection-color: #ffffff;
        }
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #d25a6d;
        }
        QTextEdit#ManuscriptEditor {
            background-color: #1a1818;
            color: #f3efec;
            border: 1px solid #403a38;
            border-radius: 10px;
            font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
            font-size: 15pt;
            line-height: 1.7;
            padding: 42px 56px;
        }
        QTreeView, QTreeWidget {
            background-color: #1b1919;
            color: #f3efec;
            border: none;
            outline: 0;
        }
        QTreeView::item, QTreeWidget::item {
            padding: 7px 5px;
            border-radius: 5px;
        }
        QTreeView::item:hover, QTreeWidget::item:hover { background-color: #352326; }
        QTreeView::item:selected, QTreeWidget::item:selected {
            background-color: #502730;
            color: #ffd9de;
        }
        QHeaderView::section {
            background-color: #1b1919;
            color: #d8d1cd;
            border: none;
            border-bottom: 1px solid #302c2b;
            padding: 8px;
            font-weight: 700;
        }
        QSplitter::handle { background-color: #302c2b; width: 1px; height: 1px; }
        QSplitter::handle:hover { background-color: #d25a6d; }
        QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
        QScrollBar::handle:vertical { background: #5b504d; border-radius: 5px; min-height: 28px; }
        QScrollBar::handle:vertical:hover { background: #887a75; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QMenu {
            background-color: #252222;
            color: #f3efec;
            border: 1px solid #403a38;
            border-radius: 8px;
            padding: 5px;
        }
        QMenu::item { padding: 7px 20px; border-radius: 4px; }
        QMenu::item:selected { background-color: #352326; color: #ffd9de; }
        QLabel#headerLabel, QLabel#StudioProjectTitle, QLabel#PanelTitle {
            color: #f8f3f0;
            font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif;
            font-weight: 700;
        }
        QLabel#headerLabel { font-size: 25px; }
        QLabel#StudioProjectTitle { font-size: 19px; }
        QLabel#PanelTitle { font-size: 22px; }
        QLabel#StudioProjectMeta, QLabel#PanelDescription, QLabel#FieldHint { color: #bdb3ae; }
        QLabel#BookCoverPreview {
            background-color: #252222;
            color: #bdb3ae;
            border: 1px solid #403a38;
            border-radius: 8px;
        }
    """

    THEMES = {
        "Juvion Claro": THEMES["Juvion"],
        "Juvion Escuro": JUVION_DARK_THEME,
    }

    ICON_TINTS = {
        "Juvion Claro": "#7b001f",
        "Juvion Escuro": "#ffb3bf",
    }

    _current_theme = "default"

    @classmethod
    def list_themes(cls):
        return list(cls.THEMES.keys())

    @classmethod
    def get_stylesheet(cls, theme_name):
        return cls.THEMES.get(theme_name, cls.THEMES["Juvion Claro"])

    @classmethod
    def apply_theme(cls, widget, theme_name):
        stylesheet = cls.get_stylesheet(theme_name)
        widget.setStyleSheet(stylesheet)
        cls.clear_icon_cache()

    @classmethod
    def apply_to_app(cls, theme_name):
        if theme_name in cls.THEMES:
            cls._current_theme = theme_name

        stylesheet = cls.get_stylesheet(theme_name)
        app = QApplication.instance()
        if app and hasattr(app, 'setStyleSheet'):
            app.setStyleSheet(stylesheet)
            cls.clear_icon_cache()
            # Emit theme change signal from the instance
            if cls._instance:
                cls._instance.themeChanged.emit(theme_name)
        else:
            raise RuntimeError(
                "No QApplication instance found. Create one before applying a theme.")


    @staticmethod
    def resolve_asset_path(file_path):
        """
        Resolves relative asset paths to absolute paths regardless of current working directory,
        executable path, or PyInstaller frozen state.
        """
        if not file_path:
            return ""
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path

        clean_rel = os.path.normpath(file_path)

        # 1. PyInstaller _MEIPASS (onefile or onedir runtime root)
        if hasattr(sys, "_MEIPASS"):
            p = os.path.join(sys._MEIPASS, clean_rel)
            if os.path.exists(p):
                return p

        # 2. Executable dir or _internal (onedir)
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            p1 = os.path.join(exe_dir, clean_rel)
            if os.path.exists(p1):
                return p1
            p2 = os.path.join(exe_dir, "_internal", clean_rel)
            if os.path.exists(p2):
                return p2

        # 3. Source directory: base dir of repository (parent of settings/)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        p3 = os.path.join(base_dir, clean_rel)
        if os.path.exists(p3):
            return p3

        # 4. Fallback: check relative to current working directory
        if os.path.exists(clean_rel):
            return os.path.abspath(clean_rel)

        return file_path

    @staticmethod
    def get_icon(file_path):
        """Returns a QIcon with the resolved asset path."""
        resolved = ThemeManager.resolve_asset_path(file_path)
        return QIcon(resolved)

    @staticmethod
    def get_tinted_icon(file_path, tint_color=None, theme_name=None, size=None):
        theme = theme_name or ThemeManager._current_theme
        if tint_color is None:
            tint_color = ThemeManager.ICON_TINTS.get(theme)
        cache_key = (file_path, str(tint_color) if isinstance(tint_color, QColor) else tint_color)

        if cache_key in ThemeManager._icon_cache:
            return ThemeManager._icon_cache[cache_key]

        resolved_path = ThemeManager.resolve_asset_path(file_path)
        renderer = QSvgRenderer(resolved_path)
        if not renderer.isValid():
            if os.path.exists(resolved_path):
                pixmap = QPixmap(resolved_path)
                if not pixmap.isNull():
                    icon = QIcon(pixmap)
                    ThemeManager._icon_cache[cache_key] = icon
                    return icon
            return QIcon()

        default_size = renderer.defaultSize()
        if size is None:
            size = default_size
        else:
            size = size if hasattr(size, 'width') else QSize(size, size)

        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        if tint_color:
            if isinstance(tint_color, str):
                tint_color = QColor(tint_color)
            elif not isinstance(tint_color, QColor):
                tint_color = QColor("white")

            tinted_pixmap = QPixmap(size)
            tinted_pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(tinted_pixmap)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.fillRect(pixmap.rect(), tint_color)
            painter.end()

            pixmap = tinted_pixmap

        icon = QIcon(pixmap)
        ThemeManager._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def calculate_contrast_ratio(cls, color1, color2):
        """Calculate the contrast ratio between two QColor objects."""
        def luminance(color):
            r, g, b = color.redF(), color.greenF(), color.blueF()
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        l1 = luminance(color1) + 0.05
        l2 = luminance(color2) + 0.05
        return max(l1, l2) / min(l1, l2)

    @classmethod
    def get_category_background_color(cls):
        """
        Return a color for category row background based on the current theme.
        """
        settings = WWSettingsManager.get_appearance_settings()
        if not settings.get("enable_category_background", True):
            return QColor(Qt.GlobalColor.transparent)

        theme = cls._current_theme
        colors = {
            "Juvion Claro": QColor("#ebe0dc"),
            "Juvion Escuro": QColor("#352326"),
            "Standard": QColor("#e0e0e0"),  # Light grey
            "Night Mode": QColor("#424242"),  # Charcoal
            "Solarized Dark": QColor("#073642"),  # Deep teal
            "Paper White": QColor("#f5f5f5"),  # Light grey
            "Ocean Breeze": QColor("#9cdae2"),  # Light blue
            "Sepia": QColor("#f9f2e5"),  # Sepia tone
            "Notion Light": QColor("#f7f7f5"),  # Light grey
            "Warm Cream": QColor("#f5e8d0"),  # Cream tone
        }
        return colors.get(theme, QColor("#f7f7f5"))  # Default to light grey

    @classmethod
    def get_theme_palette(cls, theme_name):
        """Get the color palette for a specific theme."""
        palettes = {
            "Juvion Claro": {
                "background": "#fbf9f6",
                "text": "#1b1c1a",
                "accent": "#7b001f",
                "border": "#e4e2df",
                "hover": "#ebe0dc"
            },
            "Juvion Escuro": {
                "background": "#121212",
                "text": "#f3efec",
                "accent": "#d25a6d",
                "border": "#403a38",
                "hover": "#352326"
            },
            "Standard": {
                "background": "#e0e0e0",
                "text": "black",
                "accent": "#0078d4",
                "border": "#cccccc",
                "hover": "#d0d0d0"
            },
            "Paper White": {
                "background": "#f9f9f9",
                "text": "#333333",
                "accent": "#333333",
                "border": "#cccccc",
                "hover": "#e1e1e1"
            },
            "Ocean Breeze": {
                "background": "#e0f7fa",
                "text": "#0277bd",
                "accent": "#4dd0e1",
                "border": "#0288d1",
                "hover": "#b2ebf2"
            },
            "Sepia": {
                "background": "#f4ecd8",
                "text": "#5a4630",
                "accent": "#d8c3a5",
                "border": "#a67c52",
                "hover": "#c4a484"
            },
            "Night Mode": {
                "background": "#2b2b2b",
                "text": "#ffffff",
                "accent": "#ffffff",
                "border": "#555555",
                "hover": "#444444"
            },
            "Solarized Dark": {
                "background": "#002b36",
                "text": "#839496",
                "accent": "#586e75",
                "border": "#586e75",
                "hover": "#073642"
            },
            "Notion Light": {
                "background": "#ffffff",
                "text": "#37352f",
                "accent": "#0066cc",
                "border": "#e0e0e0",
                "hover": "#f0f0f0"
            },
            "Warm Cream": {
                "background": "#fdfcfa",
                "text": "#4a4239",
                "accent": "#c9996b",
                "border": "#e8e0d8",
                "hover": "#f5e8d6"
            },
        }
        return palettes.get(theme_name, palettes["Juvion Claro"])

    @classmethod
    def clear_icon_cache(cls):
        """Clear the icon cache to force re-tinting with new theme colors."""
        cls._icon_cache.clear()

    @classmethod
    def refresh_all_icons(cls):
        """Refresh all icons in the application with current theme colors."""
        cls.clear_icon_cache()
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            # Force a repaint of all widgets
            for widget in app.allWidgets():
                widget.update()



if __name__ == '__main__':
    print("Available themes:")
    for theme in ThemeManager.list_themes():
        print(f" - {theme}")
