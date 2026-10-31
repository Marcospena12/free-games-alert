"""Barra de filtros rápidos por loja com chips selecionáveis e contadores."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
)

from ...sources.stores import STORE_LABELS, STORE_STYLES, get_store_style


class StoreChipButton(QPushButton):
    """Botão em formato de pílula/chip para filtrar uma loja específica."""

    def __init__(self, store_slug: str, count: int = 0, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.store_slug = store_slug
        self.count = count
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_appearance()

    def set_count(self, count: int) -> None:
        self.count = count
        self._update_appearance()

    def _update_appearance(self) -> None:
        style = get_store_style(self.store_slug)
        label = style.get("short", STORE_LABELS.get(self.store_slug, self.store_slug.title()))
        symbol = style.get("icon_symbol", "🎮")
        self.setText(f"{symbol} {label} ({self.count})")
        self.setObjectName("storeChip")

        # Estilo dinâmico com a cor da marca
        bg = style.get("bg", "#1e293b")
        border = style.get("border", "#475569")
        text_color = style.get("text", "#ffffff")

        self.setStyleSheet(f"""
            QPushButton#storeChip {{
                background-color: #1a2230;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 14px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#storeChip:hover {{
                background-color: #243044;
                border-color: #475569;
                color: #f1f5f9;
            }}
            QPushButton#storeChip:checked {{
                background-color: {bg};
                border: 1px solid {border};
                color: {text_color};
            }}
        """)


class StoreFilterBar(QFrame):
    """Barra horizontal com chips interativos de lojas e botões de atalho."""

    selection_changed = Signal(object)  # Emite set[str] com os slugs selecionados

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._chips: dict[str, StoreChipButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("storeFilterBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        icon_label = QLabel("🎮 Filtrar por loja:")
        icon_label.setStyleSheet("font-weight: bold; color: #cbd5e1; font-size: 12px;")
        layout.addWidget(icon_label)

        # Área de rolagem para os chips caso haja muitas lojas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFixedHeight(38)

        scroll_content = QWidget()
        self._chips_layout = QHBoxLayout(scroll_content)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Botões Todos / Nenhum
        self._btn_all = QPushButton("Todas")
        self._btn_all.setObjectName("quickFilterBtn")
        self._btn_all.setToolTip("Marcar todas as lojas")
        self._btn_all.clicked.connect(self._select_all)

        self._btn_none = QPushButton("Limpar")
        self._btn_none.setObjectName("quickFilterBtn")
        self._btn_none.setToolTip("Desmarcar todas")
        self._btn_none.clicked.connect(self._select_none)

        layout.addWidget(self._btn_all)
        layout.addWidget(self._btn_none)

    def update_stores(self, store_counts: dict[str, int]) -> None:
        """Atualiza os chips de loja com os contadores de ofertas ativas."""
        existing_selected = self.get_selected_stores()
        had_chips = len(self._chips) > 0

        # Lojas que têm pelo menos 1 oferta ou já existem
        for slug in STORE_LABELS.keys():
            count = store_counts.get(slug, 0)
            if slug not in self._chips:
                chip = StoreChipButton(slug, count)
                if had_chips and slug not in existing_selected:
                    chip.setChecked(False)
                chip.toggled.connect(self._on_chip_toggled)
                self._chips[slug] = chip
                self._chips_layout.addWidget(chip)
            else:
                self._chips[slug].set_count(count)

            # Esconde lojas sem nenhuma oferta para manter a barra limpa
            self._chips[slug].setVisible(count > 0 or slug in ("steam", "epic-games-store", "gog"))

    def get_selected_stores(self) -> set[str]:
        """Retorna os slugs de lojas atualmente marcados na barra."""
        return {slug for slug, chip in self._chips.items() if chip.isChecked()}

    def _on_chip_toggled(self) -> None:
        self.selection_changed.emit(self.get_selected_stores())

    def _select_all(self) -> None:
        for chip in self._chips.values():
            chip.blockSignals(True)
            chip.setChecked(True)
            chip.blockSignals(False)
        self.selection_changed.emit(self.get_selected_stores())

    def _select_none(self) -> None:
        for chip in self._chips.values():
            chip.blockSignals(True)
            chip.setChecked(False)
            chip.blockSignals(False)
        self.selection_changed.emit(self.get_selected_stores())
