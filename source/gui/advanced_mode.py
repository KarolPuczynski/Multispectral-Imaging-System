import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QLineEdit, QGroupBox, QMessageBox,
    QWidget, QFrame, QTabWidget, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


DARK_QSS = """
QDialog {
    background: #0f1117;
}
QWidget {
    background: #0f1117;
    color: #c8ccd4;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #1e2128;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    color: #c8ccd4;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #c8ccd4;
    font-size: 10px;
    text-transform: uppercase;
}
QPushButton {
    background: #1a1d24;
    border: 1px solid #3a3d46;
    border-radius: 5px;
    padding: 5px 14px;
    color: #c8ccd4;
    font-size: 12px;
}
QPushButton:hover {
    background: #232730;
    border-color: #4a4d56;
    color: #ffffff;
}
QPushButton:pressed {
    background: #0d0f14;
}
QPushButton#btn_save {
    background: #0e2a3d;
    border-color: #2060a0;
    color: #7ec8f0;
}
QPushButton#btn_save:hover {
    background: #0f3350;
}
QPushButton#btn_send {
    background: #0d2620;
    border-color: #2d8070;
    color: #2dcaa5;
    min-width: 70px;
}
QPushButton#btn_send:hover {
    background: #0f3028;
}
QPushButton#btn_refresh {
    background: #1a1d24;
    border-color: #3a3d46;
    color: #c8ccd4;
}
QPushButton#btn_refresh:hover {
    background: #232730;
    color: #ffffff;
    border-color: #4a4d56;
}
QComboBox {
    background: #1a1d24;
    border: 1px solid #4a4d56;
    border-radius: 5px;
    padding: 4px 8px;
    color: #ffffff;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    min-height: 28px;
}
QComboBox:focus {
    border-color: #2dcaa5;
}
QComboBox QAbstractItemView {
    background: #1a1d24;
    border: 1px solid #4a4d56;
    selection-background-color: #2dcaa5;
    selection-color: #0f1117;
    color: #ffffff;
    outline: none;
    padding: 6px;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 4px 8px;
}
QLineEdit {
    background: #181b22;
    border: 1px solid #3a3d46;
    border-radius: 4px;
    padding: 5px 8px;
    color: #c8ccd4;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #1d5040;
}
QLineEdit:focus {
    border-color: #2dcaa5;
}
QTextEdit {
    background: #050507;
    border: 1px solid #1e2128;
    border-radius: 5px;
    color: #2dcaa5;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #0d2620;
    padding: 6px;
}
QScrollBar:vertical {
    background: #0d0f14;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2a2d36;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #3a3d46;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QMessageBox {
    background: #0f1117;
}
QMessageBox QLabel {
    color: #c8ccd4;
}
QPushButton#qt_msgbox_button {
    min-width: 80px;
}
QFrame#sep {
    background: #1e2128;
    max-height: 1px;
    min-height: 1px;
}
QLabel#section {
    color: #e2e4ea;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#title {
    color: #e2e4ea;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.5px;
    background: transparent;
}
QLabel#subtitle {
    color: #888d99;
    font-size: 11px;
    background: transparent;
}
QLabel#fld {
    color: #c8ccd4;
    background: transparent;
}
QLabel#hint {
    color: #666c7a;
    font-size: 11px;
    font-family: Consolas, monospace;
    background: transparent;
}
QPushButton#btn_quick {
    font-family: Consolas, monospace;
    font-size: 11px;
    padding: 3px 6px;
    color: #c8ccd4;
    border: 1px solid #3a3d46;
}
QPushButton#btn_quick:hover {
    color: #ffffff;
    border-color: #4a4d56;
}
QTabWidget::pane {
    border: 1px solid #1e2128;
    border-radius: 4px;
    background: #0f1117;
    top: -1px;
}
QTabBar::tab {
    background: #0a0c10;
    color: #888d99;
    border: 1px solid #1e2128;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    color: #2dcaa5;
    background: #0f1117;
    border-color: #2dcaa5;
    border-bottom: 1px solid #0f1117;
}
QTabBar::tab:hover:!selected {
    color: #c8ccd4;
}
QRadioButton {
    color: #c8ccd4;
    font-size: 13px;
    spacing: 10px;
    padding: 6px 4px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #4a4d56;
    border-radius: 10px;
    background: #1a1d24;
}
QRadioButton::indicator:hover {
    border-color: #2dcaa5;
}
QRadioButton::indicator:checked {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.5, stop:0 #2dcaa5, stop:0.55 #2dcaa5,
        stop:0.6 #1a1d24, stop:1 #1a1d24);
    border: 2px solid #2dcaa5;
}
"""


LIGHT_QSS = """
QDialog {
    background: #f4f5f8;
}
QWidget {
    background: #f4f5f8;
    color: #1a1d24;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #d0d4dc;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    color: #1a1d24;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #1a1d24;
    font-size: 10px;
    text-transform: uppercase;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #c0c4cc;
    border-radius: 5px;
    padding: 5px 14px;
    color: #1a1d24;
    font-size: 12px;
}
QPushButton:hover {
    background: #e8eaf0;
    border-color: #909498;
    color: #000000;
}
QPushButton:pressed {
    background: #d0d4dc;
}
QPushButton#btn_save {
    background: #dbeeff;
    border-color: #1a4a6b;
    color: #0050a0;
    font-weight: 600;
}
QPushButton#btn_save:hover {
    background: #c8e2ff;
}
QPushButton#btn_send {
    background: #d8f5ec;
    border-color: #2d8070;
    color: #186550;
    min-width: 70px;
    font-weight: 600;
}
QPushButton#btn_send:hover {
    background: #c0eedf;
}
QPushButton#btn_refresh {
    background: #ffffff;
    border-color: #c0c4cc;
    color: #1a1d24;
}
QPushButton#btn_refresh:hover {
    background: #e8eaf0;
    color: #000000;
}
QComboBox {
    background: #ffffff;
    border: 1px solid #909498;
    border-radius: 5px;
    padding: 4px 8px;
    color: #1a1d24;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    min-height: 28px;
}
QComboBox:focus {
    border-color: #186550;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #909498;
    selection-background-color: #186550;
    selection-color: #ffffff;
    color: #1a1d24;
    outline: none;
    padding: 6px;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 4px 8px;
}
QLineEdit {
    background: #ffffff;
    border: 1px solid #c0c4cc;
    border-radius: 4px;
    padding: 5px 8px;
    color: #1a1d24;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #b8e0d0;
}
QLineEdit:focus {
    border-color: #186550;
}
QTextEdit {
    background: #ffffff;
    border: 1px solid #c0c4cc;
    border-radius: 5px;
    color: #186550;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #b8e0d0;
    padding: 6px;
}
QScrollBar:vertical {
    background: #eef0f5;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #c0c4cc;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a4ac;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QMessageBox {
    background: #f4f5f8;
}
QMessageBox QLabel {
    color: #1a1d24;
}
QPushButton#qt_msgbox_button {
    min-width: 80px;
}
QFrame#sep {
    background: #d0d4dc;
    max-height: 1px;
    min-height: 1px;
}
QLabel#section {
    color: #1a1d24;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#title {
    color: #1a1d24;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.5px;
    background: transparent;
}
QLabel#subtitle {
    color: #606570;
    font-size: 11px;
    background: transparent;
}
QLabel#fld {
    color: #1a1d24;
    background: transparent;
}
QLabel#hint {
    color: #606570;
    font-size: 11px;
    font-family: Consolas, monospace;
    background: transparent;
}
QPushButton#btn_quick {
    font-family: Consolas, monospace;
    font-size: 11px;
    padding: 3px 6px;
    color: #1a1d24;
    border: 1px solid #c0c4cc;
}
QPushButton#btn_quick:hover {
    color: #000000;
    border-color: #909498;
}
QTabWidget::pane {
    border: 1px solid #d0d4dc;
    border-radius: 4px;
    background: #f4f5f8;
    top: -1px;
}
QTabBar::tab {
    background: #e8eaf0;
    color: #606570;
    border: 1px solid #d0d4dc;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    color: #186550;
    background: #f4f5f8;
    border-color: #186550;
    border-bottom: 1px solid #f4f5f8;
}
QTabBar::tab:hover:!selected {
    color: #1a1d24;
}
QRadioButton {
    color: #1a1d24;
    font-size: 13px;
    spacing: 10px;
    padding: 6px 4px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #909498;
    border-radius: 10px;
    background: #ffffff;
}
QRadioButton::indicator:hover {
    border-color: #186550;
}
QRadioButton::indicator:checked {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.5, stop:0 #186550, stop:0.55 #186550,
        stop:0.6 #ffffff, stop:1 #ffffff);
    border: 2px solid #186550;
}
"""


def _sep():
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setObjectName("section")
    return lbl


class AdvancedSettingsDialog(QDialog):
    """
    A dialog window for advanced settings related to GRBL configuration and direct G-CODE command input.
    It allows users to select and save the COM port for the platform and PWM controller,
    and provides a console interface to send commands directly to GRBL and view responses.
    """
    NO_PORTS_TEXT = "brak portów"

    def __init__(self, parent=None, platform=None, pwm_controller=None,
                 theme="dark", on_theme_change=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia")
        self.resize(620, 680)
        self.setStyleSheet(LIGHT_QSS if theme == "light" else DARK_QSS)
        self._theme = theme
        self._on_theme_change = on_theme_change

        self.platform = platform
        self.pwm_controller = pwm_controller

        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._create_grbl_tab(), "GRBL")
        tabs.addTab(self._create_theme_tab(), "Motyw")
        layout.addWidget(tabs, stretch=1)

    def _create_grbl_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(12)
        page_layout.addWidget(self._create_ports_section())
        page_layout.addWidget(_sep())
        page_layout.addWidget(self._create_console_section(), stretch=1)
        return page

    def _create_theme_tab(self):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(10)

        page_layout.addWidget(_section_label("Tryb wyświetlania"))

        self._theme_group = QButtonGroup(page)
        self.radio_dark = QRadioButton("Ciemny (Dark)")
        self.radio_light = QRadioButton("Jasny (Light)")
        self._theme_group.addButton(self.radio_dark)
        self._theme_group.addButton(self.radio_light)

        if self._theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)

        self.radio_dark.toggled.connect(
            lambda checked: checked and self._apply_theme_choice("dark")
        )
        self.radio_light.toggled.connect(
            lambda checked: checked and self._apply_theme_choice("light")
        )

        page_layout.addWidget(self.radio_dark)
        page_layout.addWidget(self.radio_light)

        page_layout.addStretch()
        return page

    def _apply_theme_choice(self, theme):
        if theme == self._theme:
            return
        self._theme = theme
        self.setStyleSheet(LIGHT_QSS if theme == "light" else DARK_QSS)
        if self._on_theme_change:
            self._on_theme_change(theme)

    def _create_ports_section(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section_label("Konfiguracja portu COM"))

        port_row = QHBoxLayout()
        lbl = QLabel("Platforma:")
        lbl.setObjectName("fld")
        lbl.setFixedWidth(190)
        port_row.addWidget(lbl)

        self.combo_grbl_port = QComboBox()
        port_row.addWidget(self.combo_grbl_port, stretch=1)
        layout.addLayout(port_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_refresh = QPushButton("Odśwież porty")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.clicked.connect(self.scan_ports)
        btn_row.addWidget(self.btn_refresh)

        self.btn_apply = QPushButton("Zapisz port")
        self.btn_apply.setObjectName("btn_save")
        self.btn_apply.clicked.connect(self.apply_ports)
        btn_row.addWidget(self.btn_apply)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return container

    def _create_console_section(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.addWidget(_section_label("Konsola GRBL"))
        layout.addLayout(header_row)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.cmd_input = QLineEdit()
        self.cmd_input.returnPressed.connect(self.send_command)
        input_row.addWidget(self.cmd_input, stretch=1)

        self.btn_send = QPushButton("Wyślij")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.clicked.connect(self.send_command)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)


        for cmd in ["$$", "$#", "$G", "$I", "$H", "$X"]:
            btn = QPushButton(cmd)
            btn.setObjectName("btn_quick")
            btn.setFixedWidth(44)
            btn.clicked.connect(lambda checked, c=cmd: self._quick_send(c))
            quick_row.addWidget(btn)

        quick_row.addStretch()
        layout.addLayout(quick_row)

        return container

    def scan_ports(self):
        self.combo_grbl_port.clear()
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.combo_grbl_port.addItems(port_names)

        if self.platform and self.platform.grbl.port in port_names:
            self.combo_grbl_port.setCurrentText(self.platform.grbl.port)

        if not port_names:
            self.combo_grbl_port.addItem(self.NO_PORTS_TEXT)

    def apply_ports(self):
        new_grbl_port = self.combo_grbl_port.currentText()
        if not new_grbl_port or new_grbl_port == self.NO_PORTS_TEXT:
            QMessageBox.warning(self, "Błąd", "Nie wybrano portu.")
            return

        if self.platform:
            self.platform.grbl.port = new_grbl_port

        QMessageBox.information(
            self,
            "Zapisano",
            f"Port GRBL zaktualizowany: {new_grbl_port}\n\n"
            "PWM oświetlenia korzysta z tego samego portu.\n"
            "Jeśli urządzenia były połączone — rozłącz je i połącz ponownie.",
        )

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        if not self.platform:
            self.console_output.append(
                '<span style="color:#e05555;">[BŁĄD] Platforma nie jest zainicjalizowana.</span>'
            )
            return

        prompt_color = "#2060a0" if self._theme == "light" else "#5baee0"
        reply_color = "#186550" if self._theme == "light" else "#2dcaa5"

        self.console_output.append(
            f'<span style="color:{prompt_color};">&gt;&gt; {cmd}</span>'
        )
        response = self.platform.grbl.send_line_blocking(cmd)
        self.console_output.append(
            f'<span style="color:{reply_color};">&lt;&lt; {response}</span>'
        )
        self.cmd_input.clear()
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

    def _quick_send(self, cmd: str):
        self.cmd_input.setText(cmd)
        self.send_command()
