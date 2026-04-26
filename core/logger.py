import logging
import time
from logging.handlers import RotatingFileHandler


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(config: dict) -> None:
    log_cfg = config.get('logging', {})
    level_name = log_cfg.get('level', 'INFO')
    log_file = log_cfg.get('log_file', 'logs/apex.log')
    max_bytes = log_cfg.get('max_bytes', 10_485_760)
    backup_count = log_cfg.get('backup_count', 5)

    level = getattr(logging, level_name.upper(), logging.INFO)
    fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    formatter = logging.Formatter(fmt)
    formatter.converter = time.gmtime  # UTC timestamps

    root = logging.getLogger()
    root.setLevel(level)

    if not root.handlers:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
