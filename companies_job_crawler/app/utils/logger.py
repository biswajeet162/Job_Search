import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class CrawlerLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that injects execution_id and company into log records."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("execution_id", self.extra.get("execution_id", "-"))
        extra.setdefault("company", self.extra.get("company", "-"))
        return msg, kwargs


class ExecutionContextFilter(logging.Filter):
    """Ensure execution_id and company fields exist on every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "execution_id"):
            record.execution_id = "-"
        if not hasattr(record, "company"):
            record.company = "-"
        return True


def setup_logging(
    logs_dir: Path,
    log_level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 10,
) -> None:
    """Configure application-wide logging with rotating file handler."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "job_crawler.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(execution_id)s] [%(company)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(ExecutionContextFilter())
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ExecutionContextFilter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def get_crawler_logger(
    name: str,
    execution_id: str,
    company: str,
) -> CrawlerLoggerAdapter:
    """Return a logger adapter scoped to a crawler execution."""
    base_logger = get_logger(name)
    return CrawlerLoggerAdapter(
        base_logger,
        {"execution_id": execution_id, "company": company},
    )
