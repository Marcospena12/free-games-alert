"""Visão de resumo: métricas, estado do monitor e publicações recentes."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import CheckResult
from ..util import fmt_datetime, fmt_price_tooltip, open_url

CARD_COLUMNS = ("Título", "Grupo", "Detectado em", "Verificado em")


def _make_card(label: str) -> tuple[QFrame, QLabel]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 12, 12, 12)
    value = QLabel("0")
    value.setObjectName("cardValue")
    label_widget = QLabel(label)
    label_widget.setObjectName("cardLabel")
    layout.addWidget(value)
    layout.addWidget(label_widget)
    return frame, value


class DashboardView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Painel de controle")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        cards = QGridLayout()
        cards.setSpacing(12)
        self._free_card, self._free_value = _make_card("Ofertas grátis agora")
        self._groups_card, self._groups_value = _make_card("Grupos cadastrados")
        self._status_card, self._status_value = _make_card("Estado do monitoramento")
        self._last_card, self._last_value = _make_card("Última verificação")
        cards.addWidget(self._free_card, 0, 0)
        cards.addWidget(self._groups_card, 0, 1)
        cards.addWidget(self._status_card, 1, 0)
        cards.addWidget(self._last_card, 1, 1)
        layout.addLayout(cards)

        recent_group = QGroupBox("Ofertas ainda grátis (100% de desconto)")
        recent_layout = QVBoxLayout(recent_group)
        self._empty = QLabel(
            "Nenhuma oferta 100% grátis no momento. "
            "As ofertas expiradas ficam no Histórico."
        )
        self._empty.setWordWrap(True)
        self._empty.setVisible(False)
        recent_layout.addWidget(self._empty)
        self._recent = QTableWidget(0, len(CARD_COLUMNS))
        self._recent.setHorizontalHeaderLabels(CARD_COLUMNS)
        self._recent.setSelectionBehavior(QTableWidget.SelectRows)
        self._recent.setEditTriggers(QTableWidget.NoEditTriggers)
        self._recent.verticalHeader().setVisible(False)
        self._recent.horizontalHeader().setStretchLastSection(True)
        self._recent.cellDoubleClicked.connect(self._open_on_double_click)
        recent_layout.addWidget(self._recent)
        layout.addWidget(recent_group, 1)

    def refresh(
        self,
        free_count: int,
        groups_count: int,
        state_text: str,
        last_check_text: str,
        recent: list[dict],
    ) -> None:
        self._free_value.setText(str(free_count))
        self._groups_value.setText(str(groups_count))
        self._status_value.setText(state_text)
        self._last_value.setText(last_check_text)

        self._empty.setVisible(not recent)
        self._recent.setVisible(bool(recent))
        self._recent.setRowCount(len(recent))
        for row, entry in enumerate(recent):
            post = entry["post"]
            store_url = post.store_url or post.publication_url or ""
            title_item = QTableWidgetItem(post.title)
            title_item.setData(Qt.ItemDataRole.UserRole, store_url)
            tooltip = fmt_price_tooltip(post)
            if store_url:
                tooltip = (tooltip + "\n" if tooltip else "") + (
                    "Duplo clique para abrir a oferta"
                )
            if tooltip:
                title_item.setToolTip(tooltip)
            self._recent.setItem(row, 0, title_item)
            self._recent.setItem(row, 1, QTableWidgetItem(entry["group_name"]))
            self._recent.setItem(
                row, 2, QTableWidgetItem(fmt_datetime(post.discovered_at))
            )
            self._recent.setItem(
                row, 3, QTableWidgetItem(fmt_datetime(post.price_checked_at))
            )
        self._recent.resizeColumnsToContents()

    def _open_on_double_click(self, row: int, _column: int) -> None:
        item = self._recent.item(row, 0)
        url = item.data(Qt.ItemDataRole.UserRole) if item else None
        if url:
            open_url(url)


def monitor_state_text(result: Optional[CheckResult], running: bool) -> str:
    if running:
        return "Verificando feeds e ofertas..."
    if result is not None and result.failed_groups:
        return f"Ocioso · {result.failed_groups} grupo(s) com erro"
    return "Ocioso"