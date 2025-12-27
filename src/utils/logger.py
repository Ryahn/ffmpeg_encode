"""Logging utilities"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    """Application logger with file and console output"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path.home() / ".video_encoder" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir / f"encode-{timestamp}.log"
        
        # Setup logger
        self.logger = logging.getLogger("VideoEncoder")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
        self._log_buffer = []
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        self._log_buffer.append(("INFO", message))
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        self._log_buffer.append(("WARNING", message))
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
        self._log_buffer.append(("ERROR", message))
    
    def success(self, message: str):
        """Log success message"""
        self.logger.info(f"SUCCESS: {message}")
        self._log_buffer.append(("SUCCESS", message))
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
        self._log_buffer.append(("DEBUG", message))
    
    def get_log_file(self) -> Path:
        """Get the log file path"""
        return self.log_file
    
    def get_recent_logs(self, count: int = 100) -> list:
        """Get recent log entries"""
        return self._log_buffer[-count:]
    
    def clear_buffer(self):
        """Clear the log buffer"""
        self._log_buffer.clear()


# Global logger instance
logger = Logger()

