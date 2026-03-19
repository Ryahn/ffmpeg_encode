"""Global Qt Style Sheet built from theme tokens (gui.theme)."""

from __future__ import annotations

from . import theme as T


def get_stylesheet() -> str:
    """Return full application QSS. Single source for dark + blue accent look."""
    return f"""
    QWidget {{
        background-color: {T.APP_BG};
        color: {T.APP_TEXT};
        font-size: 13px;
    }}
    QMainWindow {{
        background-color: {T.APP_BG};
    }}
    QTabWidget::pane {{
        border: 1px solid {T.APP_BORDER};
        background-color: {T.APP_BG_TAB};
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: {T.APP_BG_RAISED};
        color: {T.APP_TEXT_DIM};
        padding: 8px 16px;
        margin-right: 2px;
        border: 1px solid {T.APP_BORDER};
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background-color: {T.APP_BG_TAB};
        color: {T.APP_TEXT_TITLE};
        border-bottom: 1px solid {T.APP_BG_TAB};
    }}
    QTabBar::tab:hover {{
        color: {T.APP_BLUE_LIGHT};
    }}
    QPushButton {{
        background-color: {T.APP_BLUE};
        color: white;
        border: 1px solid {T.APP_BORDER};
        padding: 6px 14px;
        border-radius: 4px;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {T.APP_BLUE_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {T.APP_BLUE};
    }}
    QPushButton:disabled {{
        background-color: {T.APP_BUTTON_DISABLED_BG};
        color: {T.APP_BUTTON_DISABLED_TEXT};
    }}
    QLineEdit, QComboBox {{
        background-color: {T.APP_BG_SUNKEN};
        color: {T.APP_TEXT};
        border: 1px solid {T.APP_BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 22px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {T.APP_BG_RAISED};
        color: {T.APP_TEXT};
        selection-background-color: {T.APP_TREE_SELECTION_BG};
    }}
    QTextEdit, QPlainTextEdit {{
        background-color: {T.APP_BG_SUNKEN};
        color: {T.APP_TEXT_CMD};
        border: 1px solid {T.APP_BORDER};
        border-radius: 4px;
        padding: 6px;
        font-family: "Consolas", "Cascadia Code", monospace;
        font-size: 12px;
    }}
    QTableWidget {{
        background-color: {T.APP_TREE_ROW_BG};
        alternate-background-color: {T.APP_BG_SUNKEN};
        color: {T.APP_TEXT};
        gridline-color: {T.APP_BORDER_INNER};
        border: 1px solid {T.APP_BORDER};
        selection-background-color: {T.APP_TREE_SELECTION_BG};
        selection-color: {T.APP_TEXT};
    }}
    QHeaderView::section {{
        background-color: {T.APP_TREE_HEADING_BG};
        color: {T.APP_TEXT_HEADER};
        padding: 6px;
        border: 1px solid {T.APP_BORDER};
        font-weight: bold;
    }}
    QScrollBar:vertical {{
        background: {T.APP_BG_SUNKEN};
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {T.APP_SCROLLBAR_THUMB};
        min-height: 24px;
        border-radius: 4px;
    }}
    QScrollBar:horizontal {{
        background: {T.APP_BG_SUNKEN};
        height: 12px;
    }}
    QScrollBar::handle:horizontal {{
        background: {T.APP_SCROLLBAR_THUMB};
        min-width: 24px;
        border-radius: 4px;
    }}
    QCheckBox {{
        color: {T.APP_TEXT};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}
    QRadioButton {{
        color: {T.APP_TEXT};
        spacing: 8px;
    }}
    QLabel {{
        color: {T.APP_TEXT};
    }}
    QGroupBox {{
        border: 1px solid {T.APP_BORDER};
        margin-top: 12px;
        padding-top: 8px;
        font-weight: bold;
        color: {T.APP_TEXT_TITLE};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
    QProgressBar {{
        border: 1px solid {T.APP_BORDER};
        border-radius: 4px;
        text-align: center;
        background-color: {T.APP_BG_SUNKEN};
        color: {T.APP_TEXT};
        height: 22px;
    }}
    QProgressBar::chunk {{
        background-color: {T.APP_BLUE};
        border-radius: 3px;
    }}
    QStatusBar {{
        background-color: {T.APP_BG};
        color: {T.APP_TEXT_DIM};
        border-top: 1px solid {T.APP_BORDER};
    }}
    QToolTip {{
        background-color: {T.APP_TREE_HEADING_BG};
        color: {T.APP_TEXT};
        border: 1px solid {T.APP_BORDER};
        padding: 4px;
    }}
    QFrame#ToastFrame {{
        border-radius: 8px;
        border: 1px solid {T.APP_BORDER};
        padding: 8px;
    }}
    """
