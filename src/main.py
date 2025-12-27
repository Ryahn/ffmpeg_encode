"""Main entry point for the application"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

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


if __name__ == "__main__":
    main()

