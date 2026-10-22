"""Paleta escura inspirada na estética da Steam."""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1b2838;
    color: #c7d5e0;
    font-size: 13px;
}

QWidget#sidebar {
    background-color: #171a21;
    border-right: 1px solid #000000;
}

QPushButton#navButton {
    background-color: transparent;
    border: none;
    border-left: 3px solid transparent;
    color: #c7d5e0;
    text-align: left;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#navButton:hover {
    background-color: #2a475e;
    color: #ffffff;
}

QPushButton#navButton:checked {
    border-left: 3px solid #66c0f4;
    background-color: rgba(102, 192, 244, 0.15);
    color: #ffffff;
}

QLabel#appTitle {
    color: #66c0f4;
    font-size: 17px;
    font-weight: bold;
    padding: 16px;
    border-bottom: 1px solid #2a475e;
}

QLabel#sectionTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: bold;
}

QLabel#cardValue {
    color: #66c0f4;
    font-size: 30px;
    font-weight: bold;
}

QLabel#cardLabel {
    color: #8f98a0;
    font-size: 12px;
}

QLabel#cardFree {
    color: #a1cd44;
    font-size: 13px;
    font-weight: bold;
}

QFrame#card {
    background-color: #202d3f;
    border: 1px solid #2a475e;
    border-radius: 6px;
}

QFrame#statusRunning {
    background-color: #2a475e;
    border-radius: 4px;
    color: #66c0f4;
    padding: 4px 10px;
}

QFrame#statusOk {
    background-color: #243b2a;
    border-radius: 4px;
    color: #a1cd44;
    padding: 4px 10px;
}

QFrame#statusError {
    background-color: #4b2a2a;
    border-radius: 4px;
    color: #ff6b6b;
    padding: 4px 10px;
}

QGroupBox {
    background-color: #202d3f;
    border: 1px solid #2a475e;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #66c0f4;
}

QTableWidget {
    background-color: #171a21;
    alternate-background-color: #1f2a37;
    border: 1px solid #2a475e;
    border-radius: 4px;
    gridline-color: #2a475e;
    selection-background-color: #2a475e;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #2a475e;
    color: #ffffff;
    border: none;
    padding: 6px;
    font-weight: bold;
}

QPushButton {
    background-color: #2a475e;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 7px 14px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #33638a;
}

QPushButton:disabled {
    background-color: #1f2a37;
    color: #6b7a84;
}

QPushButton#primary {
    background-color: #66c0f4;
    color: #171a21;
}

QPushButton#primary:hover {
    background-color: #8ecef7;
}

QPushButton#danger {
    background-color: #7a2b2b;
}

QPushButton#danger:hover {
    background-color: #a03a3a;
}

QLineEdit, QSpinBox {
    background-color: #171a21;
    border: 1px solid #2a475e;
    border-radius: 4px;
    padding: 6px 8px;
    color: #c7d5e0;
    selection-background-color: #66c0f4;
}

QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #66c0f4;
}

QCheckBox {
    spacing: 8px;
}

QListWidget {
    background-color: #171a21;
    border: 1px solid #2a475e;
    border-radius: 4px;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: #171a21;
    width: 10px;
    height: 10px;
}

QScrollBar::handle {
    background: #2a475e;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0;
    width: 0;
}

QToolTip {
    background-color: #202d3f;
    color: #ffffff;
    border: 1px solid #66c0f4;
}
"""