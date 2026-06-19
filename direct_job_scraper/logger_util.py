"""Colored console logging for scrape steps."""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _COLORS = {
        "STEP": Fore.CYAN + Style.BRIGHT,
        "OK": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERR": Fore.RED + Style.BRIGHT,
        "INFO": Fore.WHITE,
        "DEBUG": Fore.LIGHTBLACK_EX,
        "JOB": Fore.MAGENTA,
        "RESET": Style.RESET_ALL,
    }
except ImportError:
    _COLORS = {k: "" for k in ("STEP", "OK", "WARN", "ERR", "INFO", "DEBUG", "JOB", "RESET")}


class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: _COLORS["DEBUG"],
        logging.INFO: _COLORS["INFO"],
        logging.WARNING: _COLORS["WARN"],
        logging.ERROR: _COLORS["ERR"],
        logging.CRITICAL: _COLORS["ERR"],
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, _COLORS["INFO"])
        msg = super().format(record)
        if getattr(record, "step", False):
            return f"{_COLORS['STEP']}{msg}{_COLORS['RESET']}"
        if getattr(record, "job_line", False):
            return f"{_COLORS['JOB']}{msg}{_COLORS['RESET']}"
        return f"{color}{msg}{_COLORS['RESET']}"


def setup_colored_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColorFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("playwright").setLevel(logging.WARNING)


def log_step(message: str, *args: Any) -> None:
    logging.getLogger("scraper.step").info(message, *args, extra={"step": True})


def log_job(message: str, *args: Any) -> None:
    logging.getLogger("scraper.job").info(message, *args, extra={"job_line": True})
