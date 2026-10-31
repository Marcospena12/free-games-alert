"""Visão de resumo moderna: métricas, barra de filtros por loja e grade de cards com capas."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...models import CheckResult, Post
from ...services.covers import CoverCacheService
from ...services.steam import is_steam_running
from ...sources.stores import normalize_store_label
from ..util import fmt_datetime, fmt_price_tooltip, open_url
from ..widgets.game_grid import GameCardGrid
from ..widgets.store_filter_bar import StoreFilterBar

CARD_COLUMNS = ("Título", "Loja", "Grupo / Fonte", "Detectado em", "Verificado em", "Ações")


def _make_card(label: str) -> tuple[QFrame, QLabel]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 14, 14, 14)
    value = QLabel("0")
    value.setObjectName("cardValue")
    label_widget = QLabel(label)
    label_widget.setObjectName("cardLabel")
    layout.addWidget(value)
    layout.addWidget(label_widget)
    return frame, value


class DashboardView(QWidget):
    mark_in_library_requested = Signal(int, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._entries: list[dict] = []
        self._cover_service = CoverCacheService(parent=self)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Painel de Ofertas")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # 1. Métricas do Topo
        cards = QGridLayout()
        cards.setSpacing(12)
        self._free_card, self._free_value = _make_card("Ofertas grátis agora")
        self._groups_card, self._groups_value = _make_card("Fontes ativas")
        self._status_card, self._status_value = _make_card("Estado do monitor")
        self._last_card, self._last_value = _make_card("Última verificação")
        cards.addWidget(self._free_card, 0, 0)
        cards.addWidget(self._groups_card, 0, 1)
        cards.addWidget(self._status_card, 1, 0)
        cards.addWidget(self._last_card, 1, 1)
        layout.addLayout(cards)

        # 2. Barra de Filtro Rápido por Loja (Chips Interativos)
        self._filter_bar = StoreFilterBar(self)
        self._filter_bar.selection_changed.connect(self._on_store_filter_changed)
        layout.addWidget(self._filter_bar)

        # 3. Cabeçalho da Seção de Jogos com Alternância de Modo (Cards / Lista)
        section_header = QHBoxLayout()
        section_title = QLabel("Jogos em Destaque (100% de desconto)")
        section_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        section_header.addWidget(section_title)
        section_header.addStretch(1)

        view_toggle_layout = QHBoxLayout()
        view_toggle_layout.setSpacing(4)
        self._view_group = QButtonGroup(self)
        self._view_group.setExclusive(True)

        self._btn_mode_cards = QPushButton("🎴 Cards")
        self._btn_mode_cards.setObjectName("viewToggleBtn")
        self._btn_mode_cards.setCheckable(True)
        self._btn_mode_cards.setChecked(True)
        self._view_group.addButton(self._btn_mode_cards)
        view_toggle_layout.addWidget(self._btn_mode_cards)

        self._btn_mode_table = QPushButton("📋 Lista")
        self._btn_mode_table.setObjectName("viewToggleBtn")
        self._btn_mode_table.setCheckable(True)
        self._view_group.addButton(self._btn_mode_table)
        view_toggle_layout.addWidget(self._btn_mode_table)

        self._btn_mode_cards.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        self._btn_mode_table.clicked.connect(lambda: self._stack.setCurrentIndex(1))

        section_header.addLayout(view_toggle_layout)
        layout.addLayout(section_header)

        # 4. Conteúdo: StackedWidget alternando entre Grade de Cards e Tabela
        self._stack = QStackedWidget()

        # Página 0: Grade de Cards Responsiva
        self._card_grid = GameCardGrid(cover_service=self._cover_service, parent=self)
        self._card_grid.mark_in_library_requested.connect(self.mark_in_library_requested.emit)
        self._stack.addWidget(self._card_grid)

        # Página 1: Tabela Tradicional
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self._empty = QLabel(
            "Nenhuma oferta 100% grátis pendente no momento.\n"
            "Os jogos já adicionados ou expirados ficam no Histórico."
        )
        self._empty.setWordWrap(True)
        self._empty.setVisible(False)
        table_layout.addWidget(self._empty)

        self._recent = QTableWidget(0, len(CARD_COLUMNS))
        self._recent.setHorizontalHeaderLabels(CARD_COLUMNS)
        self._recent.setSelectionBehavior(QTableWidget.SelectRows)
        self._recent.setEditTriggers(QTableWidget.NoEditTriggers)
        self._recent.verticalHeader().setVisible(False)
        self._recent.horizontalHeader().setStretchLastSection(True)
        self._recent.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._recent.customContextMenuRequested.connect(self._show_context_menu)
        self._recent.cellDoubleClicked.connect(self._open_on_double_click)
        table_layout.addWidget(self._recent)

        self._stack.addWidget(table_container)
        layout.addWidget(self._stack, 1)

    def _on_store_filter_changed(self, selected_stores: set[str]) -> None:
        self._card_grid.filter_by_stores(selected_stores)
        # Filtrar também a tabela para consistência
        for row in range(self._recent.rowCount()):
            item = self._recent.item(row, 1)
            # Verifica o store slug armazenado no UserRole do título
            title_item = self._recent.item(row, 0)
            store_slug = title_item.data(Qt.ItemDataRole.UserRole + 3) if title_item else "steam"
            self._recent.setRowHidden(row, store_slug not in selected_stores)

    def refresh(
        self,
        free_count: int,
        groups_count: int,
        state_text: str,
        last_check_text: str,
        recent: list[dict],
    ) -> None:
        self._entries = recent
        self._free_value.setText(str(free_count))
        self._groups_value.setText(str(groups_count))
        self._status_value.setText(state_text)
        self._last_value.setText(last_check_text)

        # 1. Contagem por loja para a barra de chips
        store_counts: dict[str, int] = {}
        for entry in recent:
            post: Post = entry["post"]
            s = getattr(post, "store", "steam") or "steam"
            store_counts[s] = store_counts.get(s, 0) + 1

        self._filter_bar.update_stores(store_counts)
        selected_stores = self._filter_bar.get_selected_stores()

        # 2. Atualizar Grade de Cards Moderna
        self._card_grid.set_entries(recent, selected_stores)

        # 3. Atualizar Tabela Legada (para compatibilidade total com testes existentes)
        self._empty.setVisible(not recent)
        self._recent.setVisible(bool(recent))
        self._recent.setRowCount(len(recent))
        steam_running = is_steam_running()

        for row, entry in enumerate(recent):
            post = entry["post"]
            store_url = post.claim_url or post.store_url or post.publication_url or ""
            title_item = QTableWidgetItem(post.title)
            title_item.setData(Qt.ItemDataRole.UserRole, store_url)
            title_item.setData(Qt.ItemDataRole.UserRole + 1, post.store_app_id)
            title_item.setData(Qt.ItemDataRole.UserRole + 2, post.id)
            title_item.setData(Qt.ItemDataRole.UserRole + 3, getattr(post, "store", "steam"))

            tooltip = fmt_price_tooltip(post)
            open_action_label = "Abrir na Steam" if steam_running else "Abrir no navegador"
            if store_url:
                tooltip = (tooltip + "\n" if tooltip else "") + (
                    f"Duplo clique para {open_action_label.lower()}"
                )
            if tooltip:
                title_item.setToolTip(tooltip)
            self._recent.setItem(row, 0, title_item)
            self._recent.setItem(row, 1, QTableWidgetItem(normalize_store_label(post.store)))
            self._recent.setItem(row, 2, QTableWidgetItem(entry["group_name"]))
            self._recent.setItem(
                row, 3, QTableWidgetItem(fmt_datetime(post.discovered_at))
            )
            self._recent.setItem(
                row, 4, QTableWidgetItem(fmt_datetime(post.price_checked_at or post.discovered_at))
            )

            # Coluna de ações
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)

            btn_open = QPushButton("Abrir na Steam" if steam_running else "Abrir")
            btn_open.setObjectName("tableAction")
            btn_open.clicked.connect(
                lambda _c, u=store_url, a=post.store_app_id: open_url(u, app_id=a)
            )

            btn_claim = QPushButton("✓ Já resgatei")
            btn_claim.setObjectName("tableActionPrimary")
            if post.id is not None:
                btn_claim.clicked.connect(
                    lambda _c, pid=post.id: self.mark_in_library_requested.emit(
                        pid, True
                    )
                )

            actions_layout.addWidget(btn_open)
            actions_layout.addWidget(btn_claim)
            self._recent.setCellWidget(row, 5, actions_widget)

        self._recent.resizeColumnsToContents()

    def _open_on_double_click(self, row: int, _column: int) -> None:
        title_item = self._recent.item(row, 0)
        if title_item is None:
            return
        store_url = title_item.data(Qt.ItemDataRole.UserRole)
        app_id = title_item.data(Qt.ItemDataRole.UserRole + 1)
        if store_url:
            open_url(store_url, app_id=app_id)

    def _show_context_menu(self, pos) -> None:
        row = self._recent.rowAt(pos.y())
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        post = entry["post"]
        store_url = post.claim_url or post.store_url or post.publication_url or ""
        steam_running = is_steam_running()

        menu = QMenu(self)
        open_label = "Abrir na Steam" if steam_running else "Abrir na loja"
        act_open = menu.addAction(open_label)
        act_lib = menu.addAction("Marcar como adicionado à biblioteca")

        action = menu.exec(self._recent.viewport().mapToGlobal(pos))
        if action == act_open and store_url:
            open_url(store_url, app_id=post.store_app_id)
        elif action == act_lib and post.id is not None:
            self.mark_in_library_requested.emit(post.id, True)


def monitor_state_text(result: Optional[CheckResult], running: bool) -> str:
    if running:
        return "Verificando feeds e ofertas..."
    if result is not None and result.failed_groups:
        return f"Ocioso · {result.failed_groups} grupo(s) com erro"
    return "Ocioso"
