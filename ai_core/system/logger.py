import logging
import sys

def setup_logger():
    logger = logging.getLogger("NeuroBoard")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - [%(process)d] - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

log = setup_logger()
