"""Visão de gerenciamento dos grupos RSS."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...database.repositories import GroupRepository
from ...models import Group


class GroupDialog(QDialog):
    """Diálogo para adicionar ou editar um grupo RSS."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        group: Optional[Group] = None,
        title: str = "Adicionar grupo",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self._group = group

        form = QFormLayout()
        self.name_edit = QLineEdit(group.name if group else "")
        self.url_edit = QLineEdit(group.url if group else "")
        self.url_edit.setPlaceholderText("https://steamcommunity.com/groups/...")
        form.addRow("Nome", self.name_edit)
        form.addRow("URL do RSS", self.url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        self.name_edit.setText(self.name_edit.text().strip())
        self.url_edit.setText(self.url_edit.text().strip())
        if not self.name_edit.text():
            QMessageBox.warning(self, "Campo obrigatório", "Informe um nome para o grupo.")
            return
        if not self.url_edit.text().lower().startswith(("http://", "https://")):
            QMessageBox.warning(self, "URL inválida", "A URL do RSS deve começar com http:// ou https://.")
            return
        self.accept()


class GroupsView(QWidget):
    data_changed = Signal()

    def __init__(self, repo: GroupRepository, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._groups: list[Group] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Grupos RSS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Somente grupos ativos são consultados pelo monitor. "
            "O grupo padrão é cadastrado automaticamente na primeira execução."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        actions = QHBoxLayout()
        self._add_btn = QPushButton("Adicionar")
        self._add_btn.setObjectName("primary")
        self._edit_btn = QPushButton("Editar")
        self._remove_btn = QPushButton("Remover")
        self._remove_btn.setObjectName("danger")
        self._toggle_btn = QPushButton("Desativar")
        actions.addWidget(self._add_btn)
        actions.addWidget(self._edit_btn)
        actions.addWidget(self._toggle_btn)
        actions.addStretch(1)
        actions.addWidget(self._remove_btn)
        layout.addLayout(actions)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(("Nome", "URL do RSS", "Situação"))
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        self._add_btn.clicked.connect(self._add_group)
        self._edit_btn.clicked.connect(self._edit_group)
        self._toggle_btn.clicked.connect(self._toggle_active)
        self._remove_btn.clicked.connect(self._remove_group)
        self._table.itemSelectionChanged.connect(self._update_buttons)

    # ----- ações ---------------------------------------------------------
    def _selected_group(self) -> Optional[Group]:
        row = self._table.currentRow()
        if 0 <= row < len(self._groups):
            return self._groups[row]
        return None

    def _update_buttons(self) -> None:
        selected = self._selected_group() is not None
        self._edit_btn.setEnabled(selected)
        self._remove_btn.setEnabled(selected)
        self._toggle_btn.setEnabled(selected)
        if selected:
            group = self._selected_group()
            if group is not None:
                self._toggle_btn.setText("Desativar" if group.active else "Ativar")

    def _add_group(self) -> None:
        dialog = GroupDialog(self, title="Adicionar grupo")
        if dialog.exec() != QDialog.Accepted:
            return
        name, url = dialog.name_edit.text(), dialog.url_edit.text()
        if self._repo.get_by_url(url) is not None:
            QMessageBox.information(self, "Já existe", "Já existe um grupo com esta URL.")
            return
        self._repo.add(name, url, active=True)
        self._notify_changed()

    def _edit_group(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        dialog = GroupDialog(self, group=group, title="Editar grupo")
        if dialog.exec() != QDialog.Accepted:
            return
        name, url = dialog.name_edit.text(), dialog.url_edit.text()
        existing = self._repo.get_by_url(url)
        if existing is not None and existing.id != group.id:
            QMessageBox.information(self, "Já existe", "Já existe um grupo com esta URL.")
            return
        assert group.id is not None
        self._repo.update(group.id, name, url, group.active)
        self._notify_changed()

    def _toggle_active(self) -> None:
        group = self._selected_group()
        if group is None or group.id is None:
            return
        self._repo.set_active(group.id, not group.active)
        self._notify_changed()

    def _remove_group(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        answer = QMessageBox.question(
            self,
            "Remover grupo",
            f"Remover o grupo '{group.name}'?\nAs publicações já armazenadas serão removidas.",
        )
        if answer != QMessageBox.Yes or group.id is None:
            return
        self._repo.delete(group.id)
        self._notify_changed()

    def _notify_changed(self) -> None:
        self.refresh()
        self.data_changed.emit()

    # ----- carregamento ---------------------------------------------------
    def refresh(self) -> None:
        self._groups = self._repo.list_all()
        self._table.setRowCount(len(self._groups))
        for row, group in enumerate(self._groups):
            self._table.setItem(row, 0, QTableWidgetItem(group.name))
            self._table.setItem(row, 1, QTableWidgetItem(group.url))
            status = QTableWidgetItem("Ativo" if group.active else "Inativo")
            status.setForeground(
                Qt.GlobalColor.green if group.active else Qt.GlobalColor.gray
            )
            self._table.setItem(row, 2, status)
        self._table.resizeColumnsToContents()
        self._update_buttons()