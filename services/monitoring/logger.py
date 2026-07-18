"""
Apex Autonomous Trader — Structured JSON Logging
==================================================
Configures Python's root logger to output structured JSON for 
ELK, DataDog, or basic file consumption.
"""

import logging
import json
import traceback
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_obj["exception"] = "".join(traceback.format_exception(*record.exc_info))
            
        return json.dumps(log_obj)

def setup_structured_logging(level=logging.INFO):
    """Override standard logging with JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(console_handler)
    
    # Example usage:
    # logger = logging.getLogger("aat.core")
    # logger.info("Structured logging initialized")
