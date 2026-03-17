"""Main entry point for the application"""

import sys
from pathlib import Path

from utils.config import config

# Handle PyInstaller bundled executable
if getattr(sys, 'frozen', False):
    # Running as a bundled executable
    base_path = sys._MEIPASS
else:
    # Running as a normal Python script
    base_path = str(Path(__file__).parent)
    sys.path.insert(0, base_path)

from gui.main_window import MainWindow
from utils.logger import logger


def main():
    """Main function"""
    try:
        logger.info("Starting Video Encoder GUI")
        app = MainWindow()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise
    finally:
        config.flush()


if __name__ == "__main__":
    main()

