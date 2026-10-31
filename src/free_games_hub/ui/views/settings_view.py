"""Visão de configurações da aplicação com filtros independentes por loja."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...models import MonitorError
from ...services.filters import StoreFilterConfig
from ...sources.stores import (
    DEFAULT_ENABLED_STORES,
    DEFAULT_ENABLED_TYPES,
    STORE_LABELS,
    TYPE_BETA,
    TYPE_GAME,
    TYPE_LOOT,
)
from ..util import fmt_datetime


class SettingsView(QWidget):
    interval_changed = Signal(int)
    notifications_changed = Signal(bool)
    close_to_tray_changed = Signal(bool)
    start_with_windows_changed = Signal(bool)
    test_notification_requested = Signal()
    check_requested = Signal()
    gamerpower_toggled = Signal(bool)
    store_filter_changed = Signal(str, object)  # (store_slug, StoreFilterConfig)
    copy_filter_requested = Signal(str)  # source_store_slug

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._store_filters: dict[str, StoreFilterConfig] = {}
        self._updating_ui = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Configurações")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ----- Grupo de Monitoramento Geral -----
        monitoring_group = QGroupBox("Monitoramento")
        monitoring_form = QFormLayout(monitoring_group)
        self._interval = QSpinBox()
        self._interval.setRange(1, 1440)
        self._interval.setSuffix(" min")
        self._interval.setToolTip("Intervalo entre verificações automáticas dos feeds.")
        monitoring_form.addRow("Intervalo de verificação", self._interval)

        self._notifications = QCheckBox("Notificar novas ofertas gratuitas")
        self._notifications.setToolTip("Exibe alertas no sistema para jogos 100% grátis.")
        monitoring_form.addRow(self._notifications)

        self._close_to_tray = QCheckBox("Fechar a janela para a bandeja")
        self._close_to_tray.setToolTip(
            "Ao fechar a janela, o monitor continua rodando no ícone da bandeja."
        )
        monitoring_form.addRow(self._close_to_tray)

        self._start_with_windows = QCheckBox(
            "Iniciar com o Windows (minimizado na bandeja)"
        )
        self._start_with_windows.setToolTip(
            "Cria uma entrada para o usuário atual iniciar o monitor junto com o Windows, sem abrir a janela."
        )
        monitoring_form.addRow(self._start_with_windows)

        self._check_now = QPushButton("Verificar agora")
        self._check_now.setObjectName("primary")
        self._check_now.setToolTip("Executa uma verificação manual de todas as fontes ativas.")
        self._test_notification = QPushButton("Testar notificação")
        self._test_notification.setToolTip("Envia uma notificação de teste e mostra o resultado.")
        actions = QHBoxLayout()
        actions.addWidget(self._check_now)
        actions.addWidget(self._test_notification)
        actions.addStretch(1)
        monitoring_form.addRow(actions)
        layout.addWidget(monitoring_group)

        # ----- Grupo Multi-loja & GamerPower API com Filtros Independentes -----
        sources_group = QGroupBox("Fontes Globais & Filtros por Loja")
        sources_layout = QVBoxLayout(sources_group)

        self._gamerpower_enabled = QCheckBox("Habilitar GamerPower API (Monitoramento global multi-loja)")
        self._gamerpower_enabled.setToolTip(
            "Consulta a API pública da GamerPower para detectar ofertas de várias lojas em uma única chamada."
        )
        sources_layout.addWidget(self._gamerpower_enabled)

        # Painel Seletor de Loja
        store_select_box = QFrame()
        store_select_layout = QHBoxLayout(store_select_box)
        store_select_layout.setContentsMargins(0, 4, 0, 4)

        store_select_layout.addWidget(QLabel("Configurar regras para a loja:"))
        self._store_combo = QComboBox()
        for slug, label in STORE_LABELS.items():
            self._store_combo.addItem(label, slug)
        store_select_layout.addWidget(self._store_combo)

        self._store_enabled_cb = QCheckBox("Monitorar esta loja")
        self._store_enabled_cb.setStyleSheet("font-weight: bold;")
        store_select_layout.addWidget(self._store_enabled_cb)
        store_select_layout.addStretch(1)
        sources_layout.addWidget(store_select_box)

        # Painel de Detalhes da Loja Selecionada
        self._details_group = QGroupBox("Regras de filtro para a loja selecionada")
        details_layout = QVBoxLayout(self._details_group)

        types_label = QLabel("Tipos de ofertas aceitos:")
        types_label.setStyleSheet("font-weight: bold; margin-top: 2px;")
        details_layout.addWidget(types_label)
        types_row = QHBoxLayout()
        self._type_game_cb = QCheckBox("Jogos completos")
        self._type_loot_cb = QCheckBox("DLCs e Itens")
        self._type_beta_cb = QCheckBox("Betas e Acesso antecipado")
        types_row.addWidget(self._type_game_cb)
        types_row.addWidget(self._type_loot_cb)
        types_row.addWidget(self._type_beta_cb)
        types_row.addStretch(1)
        details_layout.addLayout(types_row)

        price_form = QFormLayout()
        self._min_worth_spin = QDoubleSpinBox()
        self._min_worth_spin.setRange(0.0, 999.0)
        self._min_worth_spin.setDecimals(2)
        self._min_worth_spin.setPrefix("$ ")
        self._min_worth_spin.setSpecialValueText("Sem valor mínimo")
        self._min_worth_spin.setToolTip("Descarta ofertas cujo valor original em USD seja inferior a este valor.")
        price_form.addRow("Valor mínimo estimado:", self._min_worth_spin)

        self._include_na_cb = QCheckBox("Aceitar ofertas com valor não informado (N/A)")
        self._include_na_cb.setToolTip("Muitos jogos gratuitos de qualidade não informam valor comercial em dólar.")
        price_form.addRow(self._include_na_cb)

        self._ignore_no_end_date = QCheckBox("Ignorar ofertas sem data de término definida")
        self._ignore_no_end_date.setToolTip("Descarta ofertas que não possuem prazo de expiração estabelecido.")
        price_form.addRow(self._ignore_no_end_date)

        self._exclude_keywords_edit = QLineEdit()
        self._exclude_keywords_edit.setPlaceholderText("ex: trial, demo, prologue, playtest (separadas por vírgula)")
        self._exclude_keywords_edit.setToolTip("Descarta qualquer publicação cujo título contenha alguma destas palavras.")
        price_form.addRow("Palavras a excluir:", self._exclude_keywords_edit)
        details_layout.addLayout(price_form)

        # Botão de cópia rápida
        action_row = QHBoxLayout()
        self._copy_to_all_btn = QPushButton("Copiar filtros desta loja para todas as outras")
        self._copy_to_all_btn.setToolTip("Aplica os mesmos tipos, valores e regras de exclusão para todas as demais lojas.")
        action_row.addWidget(self._copy_to_all_btn)
        action_row.addStretch(1)
        details_layout.addLayout(action_row)

        sources_layout.addWidget(self._details_group)

        # Atribuição legal da GamerPower
        attr_label = QLabel(
            'Dados de ofertas multi-lojas fornecidos gratuitamente por '
            '<a href="https://www.gamerpower.com" style="color: #66c0f4;">GamerPower.com</a>'
        )
        attr_label.setOpenExternalLinks(True)
        attr_label.setStyleSheet("font-size: 11px; margin-top: 6px; color: #8f98a0;")
        sources_layout.addWidget(attr_label)

        layout.addWidget(sources_group)

        # ----- Grupo de Erros Recentes -----
        errors_group = QGroupBox("Erros recentes do monitoramento")
        errors_layout = QVBoxLayout(errors_group)
        self._errors = QListWidget()
        self._errors.setAlternatingRowColors(True)
        errors_layout.addWidget(self._errors)
        layout.addWidget(errors_group, 1)

        # Conectar eventos de controle
        self._interval.valueChanged.connect(
            lambda _v: self.interval_changed.emit(self._interval.value())
        )
        self._notifications.toggled.connect(self.notifications_changed.emit)
        self._close_to_tray.toggled.connect(self.close_to_tray_changed.emit)
        self._start_with_windows.toggled.connect(self.start_with_windows_changed.emit)
        self._gamerpower_enabled.toggled.connect(self.gamerpower_toggled.emit)
        self._test_notification.clicked.connect(self.test_notification_requested.emit)
        self._check_now.clicked.connect(self.check_requested.emit)

        # Conectar eventos de filtros por loja
        self._store_combo.currentIndexChanged.connect(self._on_store_selection_changed)
        self._store_enabled_cb.toggled.connect(self._on_field_changed)
        self._type_game_cb.toggled.connect(self._on_field_changed)
        self._type_loot_cb.toggled.connect(self._on_field_changed)
        self._type_beta_cb.toggled.connect(self._on_field_changed)
        self._min_worth_spin.valueChanged.connect(self._on_field_changed)
        self._include_na_cb.toggled.connect(self._on_field_changed)
        self._ignore_no_end_date.toggled.connect(self._on_field_changed)
        self._exclude_keywords_edit.editingFinished.connect(self._on_field_changed)
        self._copy_to_all_btn.clicked.connect(self._on_copy_to_all_clicked)

    def _current_store_slug(self) -> str:
        return self._store_combo.currentData() or "steam"

    def _on_store_selection_changed(self) -> None:
        self._update_details_from_model(self._current_store_slug())

    def _update_details_from_model(self, slug: str) -> None:
        cfg = self._store_filters.get(
            slug,
            StoreFilterConfig(
                enabled=slug in DEFAULT_ENABLED_STORES,
                allowed_types={TYPE_GAME},
            ),
        )

        self._updating_ui = True
        store_name = STORE_LABELS.get(slug, slug.title())
        self._details_group.setTitle(f"Regras de filtro para {store_name}")

        self._store_enabled_cb.setChecked(cfg.enabled)
        self._type_game_cb.setChecked(TYPE_GAME in cfg.allowed_types)
        self._type_loot_cb.setChecked(TYPE_LOOT in cfg.allowed_types)
        self._type_beta_cb.setChecked(TYPE_BETA in cfg.allowed_types)

        self._min_worth_spin.setValue(cfg.min_worth_usd if cfg.min_worth_usd is not None else 0.0)
        self._include_na_cb.setChecked(cfg.include_na_worth)
        self._ignore_no_end_date.setChecked(cfg.ignore_no_end_date)
        self._exclude_keywords_edit.setText(", ".join(cfg.title_exclude_keywords))
        self._updating_ui = False

    def _on_field_changed(self) -> None:
        if self._updating_ui:
            return

        slug = self._current_store_slug()
        allowed: set[str] = set()
        if self._type_game_cb.isChecked():
            allowed.add(TYPE_GAME)
        if self._type_loot_cb.isChecked():
            allowed.add(TYPE_LOOT)
        if self._type_beta_cb.isChecked():
            allowed.add(TYPE_BETA)

        val = self._min_worth_spin.value()
        min_worth = val if val > 0 else None

        kw_raw = self._exclude_keywords_edit.text()
        keywords = [k.strip().lower() for k in kw_raw.split(",") if k.strip()]

        cfg = StoreFilterConfig(
            enabled=self._store_enabled_cb.isChecked(),
            allowed_types=allowed if allowed else {TYPE_GAME},
            min_worth_usd=min_worth,
            include_na_worth=self._include_na_cb.isChecked(),
            title_exclude_keywords=keywords,
            ignore_no_end_date=self._ignore_no_end_date.isChecked(),
        )

        self._store_filters[slug] = cfg
        self.store_filter_changed.emit(slug, cfg)

    def _on_copy_to_all_clicked(self) -> None:
        slug = self._current_store_slug()
        self.copy_filter_requested.emit(slug)

    def load(
        self,
        *,
        interval_minutes: int,
        notifications_enabled: bool,
        close_to_tray: bool,
        tray_available: bool,
        start_with_windows: bool,
        start_with_windows_supported: bool,
        errors: list[MonitorError],
        gamerpower_enabled: bool = True,
        store_filters: Optional[dict[str, StoreFilterConfig]] = None,
        enabled_stores: Optional[list[str]] = None,
        enabled_types: Optional[list[str]] = None,
        ignore_no_end_date: bool = False,
    ) -> None:
        self._interval.blockSignals(True)
        self._interval.setValue(interval_minutes)
        self._interval.blockSignals(False)

        self._notifications.blockSignals(True)
        self._notifications.setChecked(notifications_enabled)
        self._notifications.blockSignals(False)

        self._close_to_tray.blockSignals(True)
        self._close_to_tray.setChecked(close_to_tray)
        self._close_to_tray.setEnabled(tray_available)
        self._close_to_tray.blockSignals(False)

        self._start_with_windows.blockSignals(True)
        self._start_with_windows.setChecked(start_with_windows)
        self._start_with_windows.setEnabled(start_with_windows_supported)
        self._start_with_windows.blockSignals(False)

        self._gamerpower_enabled.blockSignals(True)
        self._gamerpower_enabled.setChecked(gamerpower_enabled)
        self._gamerpower_enabled.blockSignals(False)

        if store_filters:
            self._store_filters = store_filters
        elif enabled_stores:
            for s in STORE_LABELS.keys():
                self._store_filters[s] = StoreFilterConfig(
                    enabled=s in enabled_stores,
                    allowed_types=set(enabled_types) if enabled_types else {TYPE_GAME},
                    ignore_no_end_date=ignore_no_end_date,
                )

        # Atualizar os campos da loja atualmente selecionada
        self._update_details_from_model(self._current_store_slug())

        self._errors.clear()
        for error in errors:
            text = f"{fmt_datetime(error.created_at)} — {error.message}"
            self._errors.addItem(text)
        if not errors:
            self._errors.addItem("Nenhum erro registrado até o momento.")
