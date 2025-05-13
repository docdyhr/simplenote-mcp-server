#!/usr/bin/env python
import logging
import os

def setup_logging(module_name: str, log_file: str) -> logging.Logger:
    """Setup logging for a given module."""
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)

    # Only add handlers if they don't exist
    if not logger.handlers:
        # Add console handler for interactive use
        console = logging.StreamHandler()
        console.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        console.setLevel(logging.INFO)
        logger.addHandler(console)

        # Add file handler for debugging
        if os.environ.get("DEBUG_PATCH", "").lower() in ("1", "true", "yes"):
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)

    return logger