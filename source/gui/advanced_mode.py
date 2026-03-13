import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTextEdit, QLineEdit, 
                             QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt

class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None, platform=None, pwm_controller=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia Zaawansowane i Konsola GRBL")
        self.resize(600, 700)
        
        self.platform = platform
        self.pwm_controller = pwm_controller

        self.init_ui()
        self.scan_ports()

    def init_ui(self):
        layout = QVBoxLayout()

        # --- SEKCJA 1: Konfiguracja Portów COM ---
        ports_group = QGroupBox("Konfiguracja Portów COM")
        ports_layout = QVBoxLayout()

        # Wybór portu dla Platformy (GRBL)
        h_layout_grbl = QHBoxLayout()
        h_layout_grbl.addWidget(QLabel("Platforma (GRBL):"))
        self.combo_grbl_port = QComboBox()
        h_layout_grbl.addWidget(self.combo_grbl_port)
        ports_layout.addLayout(h_layout_grbl)

        # Wybór portu dla Oświetlenia (PWM)
        h_layout_pwm = QHBoxLayout()
        h_layout_pwm.addWidget(QLabel("Oświetlenie (PWM):"))
        self.combo_pwm_port = QComboBox()
        h_layout_pwm.addWidget(self.combo_pwm_port)
        ports_layout.addLayout(h_layout_pwm)

        # Przycisk odświeżania i zapisywania
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Odśwież listę portów")
        self.btn_refresh.clicked.connect(self.scan_ports)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_apply = QPushButton("Zapisz porty")
        self.btn_apply.clicked.connect(self.apply_ports)
        btn_layout.addWidget(self.btn_apply)
        
        ports_layout.addLayout(btn_layout)
        ports_group.setLayout(ports_layout)
        layout.addWidget(ports_group)

        # --- SEKCJA 2: Konsola GRBL ---
        console_group = QGroupBox("Konsola GRBL (Bezpośrednie komendy)")
        console_layout = QVBoxLayout()

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background-color: black; color: #00FF00; font-family: Consolas;")
        console_layout.addWidget(self.console_output)

        input_layout = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Wpisz komendę G-Code (np. $$, $#, G0 X10)...")
        self.cmd_input.returnPressed.connect(self.send_command)
        input_layout.addWidget(self.cmd_input)

        self.btn_send = QPushButton("Wyślij")
        self.btn_send.clicked.connect(self.send_command)
        input_layout.addWidget(self.btn_send)

        console_layout.addLayout(input_layout)
        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        self.setLayout(layout)

    def scan_ports(self):
        self.combo_grbl_port.clear()
        self.combo_pwm_port.clear()

        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        
        self.combo_grbl_port.addItems(port_names)
        self.combo_pwm_port.addItems(port_names)

        # Ustawienie aktualnych wartości
        if self.platform and self.platform.grbl.port in port_names:
            self.combo_grbl_port.setCurrentText(self.platform.grbl.port)
        
        if self.pwm_controller and self.pwm_controller.port in port_names:
            self.combo_pwm_port.setCurrentText(self.pwm_controller.port)

    def apply_ports(self):
        new_grbl_port = self.combo_grbl_port.currentText()
        new_pwm_port = self.combo_pwm_port.currentText()

        if self.platform:
            self.platform.grbl.port = new_grbl_port
        
        if self.pwm_controller:
            self.pwm_controller.port = new_pwm_port

        QMessageBox.information(self, "Sukces", f"Zaktualizowano porty:\nGRBL: {new_grbl_port}\nPWM: {new_pwm_port}\n\nJeśli urządzenia były połączone, rozłącz je i połącz ponownie w głównym oknie.")

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if cmd and self.platform:
            self.console_output.append(f">> {cmd}")
            response = self.platform.grbl.send_line_blocking(cmd)
            self.console_output.append(f"<< {response}")
            self.cmd_input.clear()