"""Visão do histórico de jogos gratuitos encontrados."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database.repositories import PostRepository
from ..util import fmt_datetime, fmt_post_status, fmt_price_tooltip, open_url

COLUMNS = ("Título", "Grupo", "Publicado em", "Detectado em", "Status")

FILTERS = (
    ("Todas", None),
    ("Ainda grátis", "free"),
    ("Expiradas", "not_free"),
    ("F2P (não é promoção)", "f2p"),
    ("Não verificadas", "unchecked"),
)


class HistoryView(QWidget):
    check_requested = Signal()

    def __init__(self, repo: PostRepository, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._rows: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Histórico de jogos")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Duplo clique em uma linha para abrir a oferta. "
            "Quando não houver link da loja, a publicação original no Steam é aberta."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        actions = QHBoxLayout()
        actions.addWidget(QLabel("Mostrar:"))
        self._filter = QComboBox()
        for label, value in FILTERS:
            self._filter.addItem(label, value)
        actions.addWidget(self._filter)
        self._open_store = QPushButton("Abrir oferta na loja")
        self._open_store.setObjectName("primary")
        self._open_publication = QPushButton("Abrir publicação")
        self._refresh_btn = QPushButton("Atualizar")
        self._check_prices = QPushButton("Verificar preços")
        actions.addWidget(self._open_store)
        actions.addWidget(self._open_publication)
        actions.addStretch(1)
        actions.addWidget(self._check_prices)
        actions.addWidget(self._refresh_btn)
        layout.addLayout(actions)

        group = QGroupBox("Publicações armazenadas")
        group_layout = QVBoxLayout(group)
        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        group_layout.addWidget(self._table)
        layout.addWidget(group, 1)

        self._open_store.clicked.connect(self._open_selected_store)
        self._open_publication.clicked.connect(self._open_selected_publication)
        self._refresh_btn.clicked.connect(self.refresh)
        self._filter.currentIndexChanged.connect(lambda _index: self.refresh())
        self._check_prices.clicked.connect(self.check_requested.emit)
        self._table.cellDoubleClicked.connect(self._open_on_double_click)

    # ----- ações ---------------------------------------------------------
    def _selected_row(self) -> Optional[dict]:
        row = self._table.currentRow()
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _open_selected_store(self) -> None:
        entry = self._selected_row()
        if entry is None:
            return
        open_url(entry["post"].store_url or entry["post"].publication_url)

    def _open_selected_publication(self) -> None:
        entry = self._selected_row()
        if entry is None:
            return
        open_url(entry["post"].publication_url)

    def _open_on_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._rows):
            entry = self._rows[row]
            open_url(entry["post"].store_url or entry["post"].publication_url)

    # ----- carregamento ---------------------------------------------------
    def refresh(self) -> None:
        self._rows = self._repo.list_recent(
            limit=500, status=self._filter.currentData()
        )
        self._table.setRowCount(len(self._rows))
        for row, entry in enumerate(self._rows):
            post = entry["post"]
            self._table.setItem(row, 0, QTableWidgetItem(post.title))
            self._table.setItem(row, 1, QTableWidgetItem(entry["group_name"]))
            self._table.setItem(
                row, 2, QTableWidgetItem(fmt_datetime(post.published_at))
            )
            self._table.setItem(
                row, 3, QTableWidgetItem(fmt_datetime(post.discovered_at))
            )

            status_item = QTableWidgetItem(fmt_post_status(post))
            if post.price_status == "free":
                status_item.setForeground(Qt.GlobalColor.green)
            elif post.price_status == "not_free":
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            tooltip = fmt_price_tooltip(post)
            if tooltip:
                status_item.setToolTip(tooltip)
            self._table.setItem(row, 4, status_item)

            has_store = bool(post.store_url)
            self._table.item(row, 0).setForeground(
                Qt.GlobalColor.green if has_store else Qt.GlobalColor.white
            )
            if has_store:
                self._table.item(row, 0).setToolTip("Link da loja disponível")
        self._table.resizeColumnsToContents()