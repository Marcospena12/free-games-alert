"""Paleta e estilo moderno para o Gaming Hub multi-loja."""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0b0f17;
    color: #cbd5e1;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* Sidebar e Navegação */
QWidget#sidebar {
    background-color: #070a0f;
    border-right: 1px solid #1e293b;
}

QPushButton#navButton {
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: #94a3b8;
    text-align: left;
    padding: 14px 18px;
    font-size: 14px;
    font-weight: 600;
}

QPushButton#navButton:hover {
    background-color: #111827;
    color: #f8fafc;
}

QPushButton#navButton:checked {
    border-left: 3px solid #38bdf8;
    background-color: rgba(56, 189, 248, 0.12);
    color: #38bdf8;
    font-weight: bold;
}

QLabel#appTitle {
    color: #f8fafc;
    font-size: 17px;
    font-weight: 800;
    padding: 18px 16px;
    border-bottom: 1px solid #1e293b;
}

QLabel#sectionTitle {
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
}

/* Cards de Métricas do Dashboard */
QFrame#card {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
}

QFrame#card:hover {
    border-color: #334155;
}

QLabel#cardValue {
    color: #38bdf8;
    font-size: 32px;
    font-weight: 800;
}

QLabel#cardLabel {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Barra de Filtro Rápido de Lojas */
QFrame#storeFilterBar {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 2px 6px;
}

QPushButton#quickFilterBtn {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #cbd5e1;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
}

QPushButton#quickFilterBtn:hover {
    background-color: #334155;
    color: #ffffff;
}

/* Botões de alternância de visualização */
QPushButton#viewToggleBtn {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 12px;
}

QPushButton#viewToggleBtn:checked {
    background-color: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
}

/* Caixas de Grupo */
QGroupBox {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #38bdf8;
    font-size: 13px;
    font-weight: bold;
}

/* Tabelas */
QTableWidget {
    background-color: #0f172a;
    alternate-background-color: #141f32;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: #1e293b;
    selection-background-color: #1e293b;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #f8fafc;
    border: none;
    padding: 8px;
    font-weight: bold;
    font-size: 12px;
}

/* Botões Gerais */
QPushButton {
    background-color: #1e293b;
    color: #ffffff;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2e3d54;
    border-color: #475569;
}

QPushButton#primary {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
}

QPushButton#primary:hover {
    background-color: #0369a1;
}

/* Inputs e Seletores */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f1f5f9;
    selection-background-color: #0284c7;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QListWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #cbd5e1;
}

/* Barras de Rolagem */
QScrollBar:vertical, QScrollBar:horizontal {
    background: #0b0f17;
    width: 10px;
    height: 10px;
}

QScrollBar::handle {
    background: #334155;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:hover {
    background: #475569;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0;
    width: 0;
}

QToolTip {
    background-color: #0f172a;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 4px;
    padding: 4px;
}
"""
