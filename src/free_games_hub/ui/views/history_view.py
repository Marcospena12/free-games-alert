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
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database.repositories import PostRepository
from ...services.steam import is_steam_running
from ...sources.stores import STORE_LABELS, normalize_store_label
from ..util import fmt_datetime, fmt_post_status, fmt_price_tooltip, open_url

COLUMNS = ("Título", "Loja", "Grupo / Fonte", "Publicado em", "Detectado em", "Status")

FILTERS = (
    ("Todas", None),
    ("Ainda grátis", "free"),
    ("Na biblioteca", "in_library"),
    ("Expiradas", "not_free"),
    ("F2P (não é promoção)", "f2p"),
    ("Não verificadas", "unchecked"),
)


class HistoryView(QWidget):
    check_requested = Signal()
    mark_in_library_requested = Signal(int, bool)

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
            "Duplo clique em uma linha para abrir a oferta (na Steam se estiver aberta). "
            "Quando não houver link da loja, a publicação original no Steam é aberta."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        actions = QHBoxLayout()
        actions.addWidget(QLabel("Status:"))
        self._filter = QComboBox()
        for label, value in FILTERS:
            self._filter.addItem(label, value)
        actions.addWidget(self._filter)

        actions.addWidget(QLabel("Loja:"))
        self._store_combo = QComboBox()
        self._store_combo.addItem("Todas as lojas", None)
        for slug, label in STORE_LABELS.items():
            self._store_combo.addItem(label, slug)
        actions.addWidget(self._store_combo)

        self._open_store = QPushButton("Abrir na Steam" if is_steam_running() else "Abrir oferta na loja")
        self._open_store.setObjectName("primary")
        self._open_publication = QPushButton("Abrir publicação")
        self._toggle_library_btn = QPushButton("Alternar biblioteca")
        self._toggle_library_btn.setToolTip(
            "Marca ou desmarca o jogo como adicionado à sua biblioteca"
        )
        self._refresh_btn = QPushButton("Atualizar")
        self._check_prices = QPushButton("Verificar preços")
        actions.addWidget(self._open_store)
        actions.addWidget(self._open_publication)
        actions.addWidget(self._toggle_library_btn)
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
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        group_layout.addWidget(self._table)
        layout.addWidget(group, 1)

        self._open_store.clicked.connect(self._open_selected_store)
        self._open_publication.clicked.connect(self._open_selected_publication)
        self._toggle_library_btn.clicked.connect(self._toggle_selected_library)
        self._refresh_btn.clicked.connect(self.refresh)
        self._filter.currentIndexChanged.connect(lambda _index: self.refresh())
        self._store_combo.currentIndexChanged.connect(lambda _index: self.refresh())
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
        post = entry["post"]
        open_url(post.claim_url or post.store_url or post.publication_url, app_id=post.store_app_id)

    def _open_selected_publication(self) -> None:
        entry = self._selected_row()
        if entry is None:
            return
        open_url(entry["post"].publication_url)

    def _toggle_selected_library(self) -> None:
        entry = self._selected_row()
        if entry is None:
            return
        post = entry["post"]
        if post.id is not None:
            self.mark_in_library_requested.emit(post.id, not post.in_library)

    def _open_on_double_click(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._rows):
            entry = self._rows[row]
            post = entry["post"]
            open_url(post.claim_url or post.store_url or post.publication_url, app_id=post.store_app_id)

    def _show_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0 or row >= len(self._rows):
            return
        entry = self._rows[row]
        post = entry["post"]
        store_url = post.store_url or post.publication_url or ""
        steam_running = is_steam_running()

        menu = QMenu(self)
        open_label = "Abrir na Steam" if steam_running else "Abrir na loja"
        act_open_store = menu.addAction(open_label)
        act_open_pub = menu.addAction("Abrir publicação")
        lib_action_label = (
            "Remover da biblioteca"
            if post.in_library
            else "Marcar como adicionado à biblioteca"
        )
        act_toggle_lib = menu.addAction(lib_action_label)

        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == act_open_store:
            open_url(store_url, app_id=post.store_app_id)
        elif action == act_open_pub and post.publication_url:
            open_url(post.publication_url)
        elif action == act_toggle_lib and post.id is not None:
            self.mark_in_library_requested.emit(post.id, not post.in_library)

    # ----- carregamento ---------------------------------------------------
    def refresh(self) -> None:
        steam_running = is_steam_running()
        self._open_store.setText(
            "Abrir na Steam" if steam_running else "Abrir oferta na loja"
        )
        self._rows = self._repo.list_recent(
            limit=500,
            status=self._filter.currentData(),
            store=self._store_combo.currentData(),
        )
        self._table.setRowCount(len(self._rows))
        for row, entry in enumerate(self._rows):
            post = entry["post"]
            self._table.setItem(row, 0, QTableWidgetItem(post.title))
            self._table.setItem(row, 1, QTableWidgetItem(normalize_store_label(post.store)))
            self._table.setItem(row, 2, QTableWidgetItem(entry["group_name"]))
            self._table.setItem(
                row, 3, QTableWidgetItem(fmt_datetime(post.published_at))
            )
            self._table.setItem(
                row, 4, QTableWidgetItem(fmt_datetime(post.discovered_at))
            )

            status_item = QTableWidgetItem(fmt_post_status(post))
            if post.in_library:
                status_item.setForeground(Qt.GlobalColor.cyan)
            elif post.price_status == "free":
                status_item.setForeground(Qt.GlobalColor.green)
            elif post.price_status == "not_free":
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            tooltip = fmt_price_tooltip(post)
            if tooltip:
                status_item.setToolTip(tooltip)
            self._table.setItem(row, 5, status_item)

            has_store = bool(post.claim_url or post.store_url)
            self._table.item(row, 0).setForeground(
                Qt.GlobalColor.green if has_store else Qt.GlobalColor.white
            )
            if has_store:
                self._table.item(row, 0).setToolTip("Link da loja/resgate disponível")
        self._table.resizeColumnsToContents()