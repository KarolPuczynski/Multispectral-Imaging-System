import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QGroupBox,
    QMessageBox,
)


class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None, platform=None, pwm_controller=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia zaawansowane i konsola GRBL")
        self.resize(600, 700)

        self.platform = platform
        self.pwm_controller = pwm_controller

        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        layout = QVBoxLayout()

        ports_group = QGroupBox("Konfiguracja portu COM")
        ports_layout = QVBoxLayout()

        h_layout_grbl = QHBoxLayout()
        h_layout_grbl.addWidget(QLabel("Platforma i PWM (GRBL):"))
        self.combo_grbl_port = QComboBox()
        h_layout_grbl.addWidget(self.combo_grbl_port)
        ports_layout.addLayout(h_layout_grbl)

        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Odswiez liste portow")
        self.btn_refresh.clicked.connect(self.scan_ports)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_apply = QPushButton("Zapisz port")
        self.btn_apply.clicked.connect(self.apply_ports)
        btn_layout.addWidget(self.btn_apply)

        ports_layout.addLayout(btn_layout)
        ports_group.setLayout(ports_layout)
        layout.addWidget(ports_group)

        console_group = QGroupBox("Konsola GRBL (bezposrednie komendy)")
        console_layout = QVBoxLayout()

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background-color: black; color: #00FF00; font-family: Consolas;")
        console_layout.addWidget(self.console_output)

        input_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Wpisz komende G-Code (np. $$, $#, G0 X10, M3 S500)...")
        self.cmd_input.returnPressed.connect(self.send_command)
        input_layout.addWidget(self.cmd_input)

        self.btn_send = QPushButton("Wyslij")
        self.btn_send.clicked.connect(self.send_command)
        input_layout.addWidget(self.btn_send)

        console_layout.addLayout(input_layout)
        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        self.setLayout(layout)

    def scan_ports(self):
        self.combo_grbl_port.clear()

        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]

        self.combo_grbl_port.addItems(port_names)

        if self.platform and self.platform.grbl.port in port_names:
            self.combo_grbl_port.setCurrentText(self.platform.grbl.port)

    def apply_ports(self):
        new_grbl_port = self.combo_grbl_port.currentText()

        if self.platform:
            self.platform.grbl.port = new_grbl_port

        QMessageBox.information(
            self,
            "Sukces",
            "Zaktualizowano port GRBL:\n"
            f"GRBL: {new_grbl_port}\n\n"
            "PWM oswietlenia jest sterowane przez ten sam port GRBL. "
            "Jesli urzadzenia byly polaczone, rozlacz je i polacz ponownie w glownym oknie.",
        )

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if cmd and self.platform:
            self.console_output.append(f">> {cmd}")
            response = self.platform.grbl.send_line_blocking(cmd)
            self.console_output.append(f"<< {response}")
            self.cmd_input.clear()
