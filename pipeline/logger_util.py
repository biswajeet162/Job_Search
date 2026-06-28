"""Colored logging for pipeline."""

from __future__ import annotations

import logging
import sys

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    _CYAN = Fore.CYAN + Style.BRIGHT
    _RESET = Style.RESET_ALL
except ImportError:
    _CYAN = _RESET = ""


def setup_colored_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("playwright").setLevel(logging.WARNING)
