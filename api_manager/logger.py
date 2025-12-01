import logging
from pathlib import Path


def create_logger(name: str, log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{name.lower()}.log"

    # Avoid duplicate handlers
    if not logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)
    return logger
