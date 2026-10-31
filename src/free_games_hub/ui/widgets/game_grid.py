"""Grade responsiva de cards de jogos."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...models import Post
from ...services.covers import CoverCacheService
from ..util import open_url
from .game_card import GameCardWidget

CARD_WIDTH = 300
SPACING = 16


class GameCardGrid(QWidget):
    """Container com rolagem suave e grade responsiva de cards de jogos."""

    mark_in_library_requested = Signal(int, bool)

    def __init__(self, cover_service: Optional[CoverCacheService] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cover_service = cover_service
        self._cards: list[GameCardWidget] = []
        self._entries: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Mensagem de estado vazio
        self._empty_label = QLabel(
            "Nenhuma oferta encontrada para os filtros selecionados.\n"
            "Tente marcar outras lojas na barra acima ou verificar novamente."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
        self._empty_label.setVisible(False)
        main_layout.addWidget(self._empty_label)

        # Scroll área contendo o grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background-color: transparent;")

        self._container = QWidget()
        self._container.setStyleSheet("background-color: transparent;")
        self._grid_layout = QGridLayout(self._container)
        self._grid_layout.setSpacing(SPACING)
        self._grid_layout.setContentsMargins(4, 8, 4, 16)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._container)
        main_layout.addWidget(self._scroll, 1)

    def set_entries(self, entries: list[dict], selected_stores: Optional[set[str]] = None) -> None:
        """Popula a grade com os posts e filtra pelas lojas selecionadas."""
        self._entries = entries
        self._filter_and_render(selected_stores)

    def filter_by_stores(self, selected_stores: set[str]) -> None:
        """Atualiza a visibilidade dos cards conforme a seleção da barra de lojas."""
        self._filter_and_render(selected_stores)

    def _filter_and_render(self, selected_stores: Optional[set[str]] = None) -> None:
        # Limpar widgets anteriores
        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Filtrar entradas
        filtered: list[dict] = []
        for entry in self._entries:
            post: Post = entry["post"]
            store = getattr(post, "store", "steam")
            if selected_stores is None or store in selected_stores:
                filtered.append(entry)

        self._empty_label.setVisible(len(filtered) == 0)
        self._scroll.setVisible(len(filtered) > 0)

        if not filtered:
            return

        # Calcular número de colunas baseado na largura atual
        available_width = max(600, self.width() - 30)
        cols = max(1, available_width // (CARD_WIDTH + SPACING))

        for idx, entry in enumerate(filtered):
            post = entry["post"]
            group_name = entry.get("group_name")
            card = GameCardWidget(
                post,
                group_name=group_name,
                cover_service=self._cover_service,
                parent=self._container,
            )
            card.claim_requested.connect(self._on_claim)
            card.mark_in_library_requested.connect(self.mark_in_library_requested.emit)

            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _on_claim(self, url: str, app_id: Optional[int]) -> None:
        open_url(url, app_id=app_id)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Reorganizar colunas se o tamanho mudar consideravelmente
        if self._cards:
            available_width = max(600, self.width() - 30)
            new_cols = max(1, available_width // (CARD_WIDTH + SPACING))
            # Reposicionar
            for idx, card in enumerate(self._cards):
                row = idx // new_cols
                col = idx % new_cols
                self._grid_layout.addWidget(card, row, col)
