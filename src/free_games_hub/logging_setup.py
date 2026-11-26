"""Configuração de logging compartilhada entre API e aplicativo legado."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import data_dir

LOG_FILENAME = "app.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def log_path(filename: str = LOG_FILENAME) -> Path:
    """Caminho do arquivo de log dentro do diretório de dados do usuário."""
    return data_dir() / filename


def configure_logging(filename: str = LOG_FILENAME) -> Optional[Path]:
    """Configura stdout e arquivo rotativo; retorna o caminho do arquivo usado."""
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())

    path: Optional[Path] = None
    try:
        path = log_path(filename)
        handlers.append(
            RotatingFileHandler(
                path,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )
    except OSError:
        path = None

    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )
    return path
