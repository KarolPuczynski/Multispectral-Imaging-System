import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QLineEdit, QGroupBox, QMessageBox,
    QWidget, QFrame,
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
    color: #444a58;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #444a58;
    font-size: 10px;
    text-transform: uppercase;
}
QPushButton {
    background: transparent;
    border: 1px solid #2a2d36;
    border-radius: 5px;
    padding: 5px 14px;
    color: #888d99;
    font-size: 12px;
}
QPushButton:hover {
    background: #181b22;
    border-color: #3a3d46;
    color: #c8ccd4;
}
QPushButton:pressed {
    background: #0d0f14;
}
QPushButton#btn_save {
    background: #0e2a3d;
    border-color: #1a4a6b;
    color: #5baee0;
}
QPushButton#btn_save:hover {
    background: #0f3350;
}
QPushButton#btn_send {
    background: #0d2620;
    border-color: #1d5040;
    color: #2dcaa5;
    min-width: 70px;
}
QPushButton#btn_send:hover {
    background: #0f3028;
}
QPushButton#btn_refresh {
    background: transparent;
    border-color: #2a2d36;
    color: #666c7a;
}
QPushButton#btn_refresh:hover {
    color: #888d99;
    border-color: #3a3d46;
}
QComboBox {
    background: #181b22;
    border: 1px solid #2a2d36;
    border-radius: 4px;
    padding: 5px 8px;
    color: #9ee4c8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QComboBox:focus {
    border-color: #1d7a5a;
}
QComboBox::drop-down {
    border: none;
    background: #2a2d36;
    width: 20px;
    border-radius: 0 4px 4px 0;
}
QComboBox QAbstractItemView {
    background: #181b22;
    border: 1px solid #2a2d36;
    selection-background-color: #0e2a3d;
    color: #c8ccd4;
    outline: none;
}
QLineEdit {
    background: #181b22;
    border: 1px solid #2a2d36;
    border-radius: 4px;
    padding: 5px 8px;
    color: #c8ccd4;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: #1d5040;
}
QLineEdit:focus {
    border-color: #1d7a5a;
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
"""


def _sep():
    f = QFrame()
    f.setStyleSheet("background: #1e2128; max-height: 1px; min-height: 1px;")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        "color: #444a58; font-size: 10px; font-weight: 500; letter-spacing: 1px;"
    )
    return lbl


class AdvancedSettingsDialog(QDialog):
    """
    A dialog window for advanced settings related to GRBL configuration and direct G-CODE command input.
    It allows users to select and save the COM port for the platform and PWM controller,
    and provides a console interface to send commands directly to GRBL and view responses. 
    """
    def __init__(self, parent=None, platform=None, pwm_controller=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia zaawansowane — konsola GRBL")
        self.resize(620, 680)
        self.setStyleSheet(DARK_QSS)

        self.platform = platform
        self.pwm_controller = pwm_controller

        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._create_titlebar())
        layout.addWidget(_sep())
        layout.addWidget(self._create_ports_section())
        layout.addWidget(_sep())
        layout.addWidget(self._create_console_section(), stretch=1)

    def _create_titlebar(self):
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 4)

        title = QLabel("Konsola GRBL")
        title.setStyleSheet(
            "color: #e2e4ea; font-size: 14px; font-weight: 500; letter-spacing: 0.5px;"
        )
        bar_layout.addWidget(title)

        sub = QLabel("konfiguracja portów i bezpośrednie komendy G-Code")
        sub.setStyleSheet("color: #444a58; font-size: 11px;")
        bar_layout.addWidget(sub)
        bar_layout.addStretch()
        return bar

    def _create_ports_section(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(_section_label("Konfiguracja portu COM"))

        port_row = QHBoxLayout()
        lbl = QLabel("Platforma + PWM (GRBL):")
        lbl.setStyleSheet("color: #888d99;")
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

        hint = QLabel("np. $$  $#  G0 X10  M3 S500")
        hint.setStyleSheet("color: #333640; font-size: 11px; font-family: Consolas, monospace;")
        header_row.addStretch()
        header_row.addWidget(hint)
        layout.addLayout(header_row)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("Odpowiedzi GRBL pojawią się tutaj...")
        layout.addWidget(self.console_output, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Wpisz komendę G-Code...")
        self.cmd_input.returnPressed.connect(self.send_command)
        input_row.addWidget(self.cmd_input, stretch=1)

        self.btn_send = QPushButton("Wyślij")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.clicked.connect(self.send_command)
        input_row.addWidget(self.btn_send)

        layout.addLayout(input_row)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        quick_label = QLabel("Szybkie:")
        quick_label.setStyleSheet("color: #444a58; font-size: 11px;")
        quick_row.addWidget(quick_label)

        for cmd in ["$$", "$#", "$G", "$I", "$H", "$X"]:
            btn = QPushButton(cmd)
            btn.setFixedWidth(44)
            btn.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 11px;"
                "padding: 3px 6px; color: #666c7a; border-color: #1e2128;"
            )
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
            self.combo_grbl_port.addItem("— brak portów —")

    def apply_ports(self):
        new_grbl_port = self.combo_grbl_port.currentText()
        if not new_grbl_port or new_grbl_port == "— brak portów —":
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

        self.console_output.append(
            f'<span style="color:#5baee0;">&gt;&gt; {cmd}</span>'
        )
        response = self.platform.grbl.send_line_blocking(cmd)
        self.console_output.append(
            f'<span style="color:#2dcaa5;">&lt;&lt; {response}</span>'
        )
        self.cmd_input.clear()
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

    def _quick_send(self, cmd: str):
        self.cmd_input.setText(cmd)
        self.send_command()