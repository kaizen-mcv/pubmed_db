"""
Centralized logging system for the PubMed project.

Usage:
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Informational message")
    logger.warning("Warning")
    logger.error("Error", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Logs directory
LOG_DIR = Path(__file__).parent.parent.parent / 'data' / 'logs'


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    console: bool = True
) -> None:
    """
    Configure the logging system for the whole project.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file name (None = auto-generate)
        console: If True, also show logs in the console
    """
    # Create logs directory if it does not exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-generated file name if not specified
    if log_file is None:
        log_file = f"pubmed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    log_path = LOG_DIR / log_file

    # Log format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)

    handlers = [file_handler]

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        force=True  # Override previous configuration
    )

    # Silence verbose logs from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('Bio').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


# Default project logger
logger = get_logger('pubmed')
