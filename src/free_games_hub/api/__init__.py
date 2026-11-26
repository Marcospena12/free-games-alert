"""API local (FastAPI) que alimenta o shell Electron.

O pacote expõe o ``create_app`` usado pelo Electron e pelo modo de
desenvolvimento (``python -m free_games_hub.api --dev``).
"""

from .app import create_app

__all__ = ["create_app"]
