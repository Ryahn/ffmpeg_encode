"""Main entry point for the application (PyQt6)."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from utils.config import config

if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
else:
    base_path = str(Path(__file__).parent)
    sys.path.insert(0, base_path)

from gui.main_window import MainWindow
from gui.styles import get_stylesheet
from utils.logger import logger


def main() -> None:
    try:
        logger.info("Starting Video Encoder GUI (PyQt6)")
        app = QApplication(sys.argv)
        app.setStyleSheet(get_stylesheet())
        window = MainWindow()
        window.show()
        code = app.exec()
        sys.exit(code)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        config.flush()


if __name__ == "__main__":
    main()
