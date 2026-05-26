import json
import sys
import os
import threading
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QPainter, QPen, QColor

from core.acquisition import Acquisition, AcquisitionParams
from core.preset_handling import PresetManager
from hardware.platform import Platform
from hardware.led_controller import LedController
from gui.live_view import LiveViewWidget
from gui.advanced_mode import AdvancedSettingsDialog


SETTINGS_FILE = "gui/gui_settings.json"


DARK_QSS = """
QMainWindow, QDialog {
    background: #0f1117;
}
QWidget {
    background: #0f1117;
    color: #c8ccd4;
    font-size: 13px;
}
QWidget#titlebar {
    background: #0a0c10;
}
QWidget#left_panel {
    background: #0d0f14;
    border-right: 1px solid #1e2128;
}
QWidget#center_panel {
    background: #0a0c10;
}
QWidget#right_panel {
    background: #0d0f14;
    border-left: 1px solid #1e2128;
}
QWidget#controls_bar {
    background: #0d0f14;
    border-top: 1px solid #1e2128;
}
QLabel#app_title {
    color: #e2e4ea;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: 1px;
    background: transparent;
}
QFrame#info_box, QFrame#ocular_box, QFrame#active_preset_box {
    background: #181b22;
    border: 1px solid #2a2d36;
    border-radius: 5px;
}
QFrame#info_box QLabel, QFrame#ocular_box QLabel, QFrame#active_preset_box QLabel {
    background: transparent;
}
QGroupBox {
    border: 1px solid #1e2128;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 500;
    color: #c8ccd4;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #c8ccd4;
    font-size: 11px;
}
QPushButton {
    background: #1a1d24;
    border: 1px solid #3a3d46;
    border-radius: 5px;
    padding: 7px 16px;
    color: #c8ccd4;
    font-size: 13px;
    min-height: 28px;
}
QPushButton:hover {
    background: #232730;
    border-color: #4a4d56;
    color: #ffffff;
}
QPushButton:pressed {
    background: #0d0f14;
}
QPushButton:disabled {
    color: #333640;
    background: #14161c;
    border-color: #1e2128;
}
QPushButton#btn_connect:enabled {
    background: #0e2a3d;
    border-color: #2060a0;
    color: #7ec8f0;
    font-weight: 500;
}
QPushButton#btn_connect:enabled:hover {
    background: #0f3350;
    border-color: #2d80c0;
    color: #ffffff;
}
QPushButton#btn_disconnect:enabled {
    background: #2a1515;
    border-color: #6a2828;
    color: #e05555;
    font-weight: 500;
}
QPushButton#btn_disconnect:enabled:hover {
    background: #331a1a;
    border-color: #8a3535;
    color: #ff7878;
}
QPushButton#btn_scan, QPushButton#btn_capture {
    background: #0d2620;
    border-color: #2d8070;
    color: #2dcaa5;
    font-weight: 500;
    padding: 9px 16px;
    min-height: 32px;
}
QPushButton#btn_scan:hover, QPushButton#btn_capture:hover {
    background: #0f3028;
    border-color: #3da080;
    color: #5eecc8;
}
QPushButton#btn_start_live:enabled {
    background: #0d2620;
    border-color: #2d8070;
    color: #2dcaa5;
    font-weight: 500;
}
QPushButton#btn_start_live:enabled:hover {
    background: #0f3028;
    color: #5eecc8;
}
QPushButton#btn_stop_live:enabled {
    background: #2a1515;
    border-color: #6a2828;
    color: #e05555;
    font-weight: 500;
}
QPushButton#btn_stop_live:enabled:hover {
    background: #331a1a;
    border-color: #8a3535;
    color: #ff7878;
}
QPushButton#btn_close {
    background: #2a1515;
    border-color: #4a2020;
    color: #e05555;
}
QPushButton#btn_close:hover {
    background: #331a1a;
    border-color: #6a2828;
}
QPushButton#btn_save {
    background: #0e2a3d;
    border-color: #1a4a6b;
    color: #5baee0;
}
QPushButton#btn_save:hover {
    background: #0f3350;
    border-color: #2060a0;
    color: #7ec8f0;
}
QPushButton#btn_delete {
    background: #1a0d0d;
    border-color: #3d1e1e;
    color: #c05050;
    padding: 5px 8px;
    font-size: 12px;
}
QPushButton#btn_delete:hover {
    background: #2a1515;
    border-color: #6a2828;
    color: #e05555;
}
QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
    background: #1a1d24;
    border: 1px solid #4a4d56;
    border-radius: 5px;
    padding: 4px 8px;
    color: #ffffff;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    min-height: 32px;
    min-width: 80px;
    selection-background-color: #1d5040;
}
QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {
    border-color: #2dcaa5;
}
QSpinBox, QDoubleSpinBox {
    padding-right: 26px;
}
QAbstractSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    background: #2dcaa5;
    border: none;
    border-top-right-radius: 4px;
    color: #0f1117;
}
QAbstractSpinBox::up-button:hover {
    background: #5eecc8;
}
QAbstractSpinBox::up-button:pressed {
    background: #1a8a6a;
}
QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    background: #2dcaa5;
    border: none;
    border-bottom-right-radius: 4px;
    border-top: 1px solid #0f1117;
    color: #0f1117;
}
QAbstractSpinBox::down-button:hover {
    background: #5eecc8;
}
QAbstractSpinBox::down-button:pressed {
    background: #1a8a6a;
}
QComboBox QAbstractItemView {
    background: #1a1d24;
    border: 1px solid #4a4d56;
    selection-background-color: #2dcaa5;
    selection-color: #0f1117;
    color: #ffffff;
    outline: none;
    font-size: 13px;
    padding: 6px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 8px;
}
QLineEdit[readOnly="true"] {
    color: #888d99;
}
QLineEdit#path_edit {
    color: #c8ccd4;
    font-size: 11px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #2a2d36;
    border: 1px solid #3a3d46;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #2dcaa5;
    border: 2px solid #5eecc8;
    width: 22px;
    height: 22px;
    margin: -8px 0;
    border-radius: 11px;
}
QSlider::handle:horizontal:hover {
    background: #5eecc8;
    border-color: #ffffff;
}
QSlider::sub-page:horizontal {
    background: #1d7a5a;
    border-radius: 4px;
}
QCheckBox {
    color: #c8ccd4;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3a3d46;
    border-radius: 3px;
    background: #181b22;
}
QCheckBox::indicator:checked {
    background: #1d7a5a;
    border-color: #2dcaa5;
}
QTabWidget::pane {
    border: none;
    background: #0d0f14;
}
QTabWidget::tab-bar {
    alignment: left;
}
QTabBar::tab {
    background: #0a0c10;
    color: #888d99;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    color: #2dcaa5;
    border-bottom: 2px solid #2dcaa5;
    background: #0d0f14;
}
QTabBar::tab:hover {
    color: #c8ccd4;
    background: #0d0f14;
}
QFrame#separator {
    background: #1e2128;
    max-height: 1px;
    min-height: 1px;
}
QLabel#section_label {
    color: #e2e4ea;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#pos_label {
    color: #2dcaa5;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    background: transparent;
}
QLabel#pos_label_box {
    color: #2dcaa5;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    background: #0a0c10;
    border: 1px solid #1e2128;
    border-radius: 4px;
    padding: 5px;
}
QLabel#status_ok {
    color: #2dcaa5;
    font-size: 12px;
    font-weight: 500;
}
QLabel#status_err {
    color: #e05555;
    font-size: 11px;
    font-weight: 500;
}
QLabel#info_val {
    color: #c8ffe5;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    background: transparent;
}
QLabel#hint_text {
    color: #888d99;
    font-size: 10px;
    background: transparent;
}
QLabel#active_preset_lbl {
    color: #2dcaa5;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}
QMessageBox {
    background: #0f1117;
}
QMessageBox QLabel {
    color: #c8ccd4;
}
"""


LIGHT_QSS = """
QMainWindow, QDialog {
    background: #f4f5f8;
}
QWidget {
    background: #f4f5f8;
    color: #1a1d24;
    font-size: 13px;
}
QWidget#titlebar {
    background: #e8eaf0;
    border-bottom: 1px solid #d0d4dc;
}
QWidget#left_panel {
    background: #eef0f5;
    border-right: 1px solid #d0d4dc;
}
QWidget#center_panel {
    background: #f8f9fb;
}
QWidget#right_panel {
    background: #eef0f5;
    border-left: 1px solid #d0d4dc;
}
QWidget#controls_bar {
    background: #eef0f5;
    border-top: 1px solid #d0d4dc;
}
QLabel#app_title {
    color: #1a1d24;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: 1px;
    background: transparent;
}
QFrame#info_box, QFrame#ocular_box, QFrame#active_preset_box {
    background: #ffffff;
    border: 1px solid #d0d4dc;
    border-radius: 5px;
}
QFrame#info_box QLabel, QFrame#ocular_box QLabel, QFrame#active_preset_box QLabel {
    background: transparent;
    color: #1a1d24;
}
QGroupBox {
    border: 1px solid #d0d4dc;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 500;
    color: #1a1d24;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #1a1d24;
    font-size: 11px;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #c0c4cc;
    border-radius: 5px;
    padding: 7px 16px;
    color: #1a1d24;
    font-size: 13px;
    min-height: 28px;
}
QPushButton:hover {
    background: #e8eaf0;
    border-color: #909498;
    color: #000000;
}
QPushButton:pressed {
    background: #d0d4dc;
}
QPushButton:disabled {
    color: #b0b4bc;
    background: #f0f1f5;
    border-color: #e0e2e8;
}
QPushButton#btn_connect:enabled {
    background: #dbeeff;
    border-color: #2060a0;
    color: #0050a0;
    font-weight: 600;
}
QPushButton#btn_connect:enabled:hover {
    background: #c8e2ff;
    border-color: #1050a0;
    color: #003070;
}
QPushButton#btn_disconnect:enabled {
    background: #ffe0e0;
    border-color: #c04040;
    color: #a02020;
    font-weight: 600;
}
QPushButton#btn_disconnect:enabled:hover {
    background: #ffd0d0;
    border-color: #a02020;
    color: #800000;
}
QPushButton#btn_scan, QPushButton#btn_capture {
    background: #d8f5ec;
    border-color: #2d8070;
    color: #186550;
    font-weight: 600;
    padding: 9px 16px;
    min-height: 32px;
}
QPushButton#btn_scan:hover, QPushButton#btn_capture:hover {
    background: #c0eedf;
    border-color: #1a6050;
    color: #0a4030;
}
QPushButton#btn_start_live:enabled {
    background: #d8f5ec;
    border-color: #2d8070;
    color: #186550;
    font-weight: 600;
}
QPushButton#btn_start_live:enabled:hover {
    background: #c0eedf;
    color: #0a4030;
}
QPushButton#btn_stop_live:enabled {
    background: #ffe0e0;
    border-color: #c04040;
    color: #a02020;
    font-weight: 600;
}
QPushButton#btn_stop_live:enabled:hover {
    background: #ffd0d0;
    border-color: #a02020;
    color: #800000;
}
QPushButton#btn_close {
    background: #ffe0e0;
    border-color: #c04040;
    color: #a02020;
}
QPushButton#btn_close:hover {
    background: #ffd0d0;
    border-color: #a02020;
}
QPushButton#btn_save {
    background: #dbeeff;
    border-color: #1a4a6b;
    color: #0050a0;
}
QPushButton#btn_save:hover {
    background: #c8e2ff;
    color: #003070;
}
QPushButton#btn_delete {
    background: #ffe8e8;
    border-color: #c08080;
    color: #a02020;
    padding: 5px 8px;
    font-size: 12px;
}
QPushButton#btn_delete:hover {
    background: #ffd0d0;
    border-color: #a02020;
}
QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #909498;
    border-radius: 5px;
    padding: 4px 8px;
    color: #1a1d24;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    min-height: 32px;
    min-width: 80px;
    selection-background-color: #b8e0d0;
}
QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {
    border-color: #186550;
}
QSpinBox, QDoubleSpinBox {
    padding-right: 26px;
}
QAbstractSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    background: #186550;
    border: none;
    border-top-right-radius: 4px;
    color: #ffffff;
}
QAbstractSpinBox::up-button:hover {
    background: #2dcaa5;
}
QAbstractSpinBox::up-button:pressed {
    background: #0a4030;
}
QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    background: #186550;
    border: none;
    border-bottom-right-radius: 4px;
    border-top: 1px solid #ffffff;
    color: #ffffff;
}
QAbstractSpinBox::down-button:hover {
    background: #2dcaa5;
}
QAbstractSpinBox::down-button:pressed {
    background: #0a4030;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #909498;
    selection-background-color: #186550;
    selection-color: #ffffff;
    color: #1a1d24;
    outline: none;
    font-size: 13px;
    padding: 6px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 8px;
}
QLineEdit[readOnly="true"] {
    color: #606570;
}
QLineEdit#path_edit {
    color: #1a1d24;
    font-size: 11px;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #d0d4dc;
    border: 1px solid #b0b4bc;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #186550;
    border: 2px solid #2dcaa5;
    width: 22px;
    height: 22px;
    margin: -8px 0;
    border-radius: 11px;
}
QSlider::handle:horizontal:hover {
    background: #2dcaa5;
    border-color: #186550;
}
QSlider::sub-page:horizontal {
    background: #2dcaa5;
    border-radius: 4px;
}
QCheckBox {
    color: #1a1d24;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #c0c4cc;
    border-radius: 3px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #186550;
    border-color: #2dcaa5;
}
QTabWidget::pane {
    border: none;
    background: #eef0f5;
}
QTabWidget::tab-bar {
    alignment: left;
}
QTabBar::tab {
    background: #e8eaf0;
    color: #606570;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
}
QTabBar::tab:selected {
    color: #186550;
    border-bottom: 2px solid #186550;
    background: #eef0f5;
}
QTabBar::tab:hover {
    color: #1a1d24;
    background: #eef0f5;
}
QFrame#separator {
    background: #d0d4dc;
    max-height: 1px;
    min-height: 1px;
}
QLabel#section_label {
    color: #1a1d24;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    background: transparent;
}
QLabel#pos_label {
    color: #186550;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QLabel#pos_label_box {
    color: #186550;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 600;
    background: #ffffff;
    border: 1px solid #c0c4cc;
    border-radius: 4px;
    padding: 5px;
}
QLabel#status_ok {
    color: #186550;
    font-size: 12px;
    font-weight: 500;
}
QLabel#status_err {
    color: #c04040;
    font-size: 11px;
    font-weight: 500;
}
QLabel#info_val {
    color: #186550;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    background: transparent;
}
QLabel#hint_text {
    color: #606570;
    font-size: 10px;
    background: transparent;
}
QLabel#active_preset_lbl {
    color: #186550;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QMessageBox {
    background: #f4f5f8;
}
QMessageBox QLabel {
    color: #1a1d24;
}
"""


class _PlusMinusOverlay:
    """Mixin: paints big '+' / '−' labels centered over the spinbox buttons."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons:
            return

        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        style = self.style()
        up_rect = style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox, opt,
            QStyle.SubControl.SC_SpinBoxUp, self,
        )
        down_rect = style.subControlRect(
            QStyle.ComplexControl.CC_SpinBox, opt,
            QStyle.SubControl.SC_SpinBoxDown, self,
        )

        window = self.window()
        theme = getattr(window, "theme", "dark")
        color = "#0f1117" if theme == "dark" else "#ffffff"

        painter = QPainter(self)
        font = QFont(self.font())
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(color)))
        painter.drawText(up_rect, Qt.AlignmentFlag.AlignCenter, "+")
        painter.drawText(down_rect, Qt.AlignmentFlag.AlignCenter, "−")


class SpinBox(_PlusMinusOverlay, QSpinBox):
    pass


class DoubleSpinBox(_PlusMinusOverlay, QDoubleSpinBox):
    pass


def _sep():
    f = QFrame()
    f.setObjectName("separator")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def _section_label(text):
    lbl = QLabel(text.upper())
    lbl.setObjectName("section_label")
    return lbl


class App(QMainWindow):
    """
    Main application window for the Multispectral Imaging System.
    It initializes the GUI, manages the state of the application,
    and coordinates interactions between the acquisition logic, preset management, platform control, and live view display.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multispectral System")
        self.resize(1500, 860)
        self.setMinimumSize(1100, 650)

        self.save_path = os.getcwd()
        self.preset_name = None
        self.preset_mode = None
        self.preset_start_wavelength = None
        self.preset_end_wavelength = None
        self.preset_step = None
        self.preset_fov_x = None
        self.preset_fov_y = None
        self.preset_overlap = None
        self.is_live_view_running = False

        self.theme = self._load_theme_pref()

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.refresh_live_parameters)

        self.platform_connection_timer = QTimer(self)
        self.platform_connection_timer.timeout.connect(self.check_platform_connection)
        self.platform_connection_timer.start(2000)

        self.init_logic_modules()
        self.init_ui()
        self.apply_theme()
        self.update_image_format_controls()
        self._update_connection_buttons()
        self._update_live_view_buttons()

    def _load_theme_pref(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("theme", "dark")
        except Exception:
            pass
        return "dark"

    def _save_theme_pref(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({"theme": self.theme}, f)
        except Exception:
            pass

    def init_logic_modules(self):
        self.acquisition = Acquisition()
        self.presets = PresetManager("presets.json")
        self.oculars = PresetManager("oculars.json")
        self.platform = Platform()
        self.pwm_controller = LedController(self.platform.grbl)
        self.bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}

    def init_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._create_titlebar())
        root_layout.addWidget(_sep())

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._create_left_panel())
        content_layout.addWidget(self._create_center_panel(), stretch=1)
        content_layout.addWidget(self._create_right_panel())

        root_layout.addWidget(content, stretch=1)

        self._apply_plus_minus_buttons()

    def _apply_plus_minus_buttons(self):
        """Switch every interactive spinbox to native +/− buttons."""
        plus_minus = QAbstractSpinBox.ButtonSymbols.PlusMinus
        for spin in self.findChildren(QAbstractSpinBox):
            if spin.buttonSymbols() != QAbstractSpinBox.ButtonSymbols.NoButtons:
                spin.setButtonSymbols(plus_minus)

    def _create_titlebar(self):
        bar = QWidget()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = QLabel("Multispectral System")
        title.setObjectName("app_title")
        layout.addWidget(title)

        layout.addSpacing(16)

        self.cam_status_label = QLabel()
        self.set_connection_status(self.cam_status_label, "Kamera", False)
        layout.addWidget(self.cam_status_label)

        self.kur_status_label = QLabel()
        self.set_connection_status(self.kur_status_label, "KURIOS", False)
        layout.addWidget(self.kur_status_label)

        self.platform_status_label = QLabel()
        self.set_connection_status(self.platform_status_label, "Platforma", False)
        layout.addWidget(self.platform_status_label)

        layout.addStretch()

        self.btn_connect = QPushButton("Połącz")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setFixedHeight(30)
        self.btn_connect.clicked.connect(self.connect)
        layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Rozłącz")
        self.btn_disconnect.setObjectName("btn_disconnect")
        self.btn_disconnect.setFixedHeight(30)
        self.btn_disconnect.clicked.connect(self.disconnect_platform_action)
        layout.addWidget(self.btn_disconnect)

        btn_settings = QPushButton("Ustawienia")
        btn_settings.setFixedHeight(30)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)

        btn_close = QPushButton("Zakończ")
        btn_close.setObjectName("btn_close")
        btn_close.setFixedHeight(30)
        btn_close.clicked.connect(self.on_close)
        layout.addWidget(btn_close)

        return bar

    def set_theme(self, theme):
        if theme == self.theme:
            return
        self.theme = theme
        self.apply_theme()
        self._save_theme_pref()

    def apply_theme(self):
        qss = LIGHT_QSS if self.theme == "light" else DARK_QSS
        self.setStyleSheet(qss)
        # Re-paint connection-status labels (they use inline colors)
        if hasattr(self, "cam_status_label"):
            self.set_connection_status(self.cam_status_label, "Kamera", self.acquisition.camera_connected if hasattr(self, "acquisition") else False)
            self.set_connection_status(self.kur_status_label, "KURIOS", self.acquisition.kurios_connected if hasattr(self, "acquisition") else False)
            platform_conn = False
            if hasattr(self, "platform") and self.platform.grbl.ser is not None:
                platform_conn = self.platform.is_connected()
            self.set_connection_status(self.platform_status_label, "Platforma", platform_conn)

    def _create_left_panel(self):
        panel = QWidget()
        panel.setObjectName("left_panel")
        panel.setFixedWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(12)

        layout.addWidget(_section_label("Parametry"))

        param_grid = QGridLayout()
        param_grid.setSpacing(8)

        param_grid.addWidget(QLabel("λ [nm]"), 0, 0)
        self.spin_wavelength = SpinBox()
        self.spin_wavelength.setRange(450, 700)
        self.spin_wavelength.setValue(500)
        self.spin_wavelength.valueChanged.connect(self.trigger_hardware_update)
        param_grid.addWidget(self.spin_wavelength, 0, 1)

        param_grid.addWidget(QLabel("Ekspoz. [µs]"), 1, 0)
        self.spin_exposure = SpinBox()
        self.spin_exposure.setRange(100, 59269000)
        self.spin_exposure.setValue(50000)
        self.spin_exposure.valueChanged.connect(self.trigger_hardware_update)
        param_grid.addWidget(self.spin_exposure, 1, 1)

        param_grid.addWidget(QLabel("Gain"), 2, 0)
        self.spin_gain = SpinBox()
        self.spin_gain.setRange(0, 48)
        self.spin_gain.setSingleStep(1)
        self.spin_gain.setValue(0)
        self.spin_gain.valueChanged.connect(self.trigger_hardware_update)
        param_grid.addWidget(self.spin_gain, 2, 1)

        param_grid.addWidget(QLabel("Pasmo"), 3, 0)
        self.combo_bandwidth = QComboBox()
        self.combo_bandwidth.addItems(list(self.bandwidth_modes.keys()))
        self.combo_bandwidth.currentTextChanged.connect(self.trigger_hardware_update)
        param_grid.addWidget(self.combo_bandwidth, 3, 1)

        param_grid.setColumnStretch(1, 1)

        layout.addLayout(param_grid)
        layout.addWidget(_sep())

        layout.addWidget(_section_label("Oświetlenie PWM"))
        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 255)
        self.pwm_slider.setValue(128)
        self.pwm_slider.valueChanged.connect(self.adjust_lighting)
        layout.addWidget(self.pwm_slider)

        self.label_pwm_val = QLabel("128 / 255")
        self.label_pwm_val.setObjectName("info_val")
        self.label_pwm_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pwm_val)

        layout.addWidget(_sep())

        layout.addWidget(_section_label("Ścieżka zapisu"))
        self.edit_save_path = QLineEdit(self.save_path)
        self.edit_save_path.setObjectName("path_edit")
        self.edit_save_path.setReadOnly(True)
        layout.addWidget(self.edit_save_path)

        btn_path = QPushButton("Wybierz folder...")
        btn_path.clicked.connect(self.select_save_directory)
        layout.addWidget(btn_path)

        layout.addSpacing(4)
        layout.addWidget(QLabel("Format"))
        self.combo_image_format = QComboBox()
        self.image_formats = (".tiff", ".png", ".jpg")
        self.combo_image_format.addItems(self.image_formats)
        layout.addWidget(self.combo_image_format)

        layout.addStretch()
        return panel

    def _create_center_panel(self):
        panel = QWidget()
        panel.setObjectName("center_panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.live_view_widget = LiveViewWidget()
        layout.addWidget(self.live_view_widget, stretch=1)

        controls_bar = QWidget()
        controls_bar.setObjectName("controls_bar")
        controls_bar.setFixedHeight(52)
        bar_layout = QHBoxLayout(controls_bar)
        bar_layout.setContentsMargins(10, 0, 10, 0)
        bar_layout.setSpacing(8)

        self.btn_start_live = QPushButton("Start Live")
        self.btn_start_live.setObjectName("btn_start_live")
        self.btn_start_live.clicked.connect(self.start_live_view_action)
        bar_layout.addWidget(self.btn_start_live)

        self.btn_stop_live = QPushButton("Stop")
        self.btn_stop_live.setObjectName("btn_stop_live")
        self.btn_stop_live.clicked.connect(self.stop_live_view_action)
        self.btn_stop_live.setEnabled(False)
        bar_layout.addWidget(self.btn_stop_live)

        bar_layout.addSpacing(8)

        self.label_pos = QLabel("Aktualna pozycja:  X=0.00 mm  Y=0.00 mm  Z=0.00 mm")
        self.label_pos.setObjectName("pos_label")
        bar_layout.addWidget(self.label_pos)

        bar_layout.addStretch()

        layout.addWidget(controls_bar)
        return panel

    def _create_right_panel(self):
        panel = QWidget()
        panel.setObjectName("right_panel")
        panel.setFixedWidth(290)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(self._tab_presety(), "Presety")
        tabs.addTab(self._tab_xyz(), "XYZ")
        tabs.addTab(self._tab_skan(), "Skan")
        tabs.addTab(self._tab_edytor(), "Edytor")

        layout.addWidget(tabs)
        return panel

    def _tab_presety(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)

        layout.addWidget(_section_label("Aktywny preset"))

        row1 = QHBoxLayout()
        self.combo_select_preset = QComboBox()
        self.combo_select_preset.addItem("Wybierz preset")
        self.combo_select_preset.addItems(list(self.presets.get_preset_names()))
        self.combo_select_preset.currentTextChanged.connect(self.on_preset_selected)
        row1.addWidget(self.combo_select_preset)
        btn_del_preset = QPushButton("Usuń")
        btn_del_preset.setObjectName("btn_delete")
        btn_del_preset.setFixedWidth(54)
        btn_del_preset.clicked.connect(self.delete_preset_action)
        row1.addWidget(btn_del_preset)
        layout.addLayout(row1)

        info_box = QFrame()
        info_box.setObjectName("info_box")
        info_layout = QGridLayout(info_box)
        info_layout.setContentsMargins(8, 7, 8, 7)
        info_layout.setSpacing(3)

        for i, key in enumerate(["Mode", "Zakres λ", "Step", "Geometria"]):
            info_layout.addWidget(QLabel(key), i, 0)

        self.label_mode = QLabel("---")
        self.label_mode.setObjectName("info_val")
        self.label_range = QLabel("---")
        self.label_range.setObjectName("info_val")
        self.label_step = QLabel("---")
        self.label_step.setObjectName("info_val")
        self.label_geo = QLabel("---")
        self.label_geo.setObjectName("info_val")
        self.label_geo.setWordWrap(True)

        info_layout.addWidget(self.label_mode, 0, 1)
        info_layout.addWidget(self.label_range, 1, 1)
        info_layout.addWidget(self.label_step, 2, 1)
        info_layout.addWidget(self.label_geo, 3, 1)
        layout.addWidget(info_box)

        layout.addWidget(_sep())
        layout.addWidget(_section_label("Obiektyw"))

        row2 = QHBoxLayout()
        self.combo_select_ocular = QComboBox()
        self.combo_select_ocular.addItem("Wybierz obiektyw")
        self.combo_select_ocular.addItems(list(self.oculars.get_preset_names()))
        self.combo_select_ocular.currentTextChanged.connect(self.on_ocular_selected)
        row2.addWidget(self.combo_select_ocular)
        btn_del_ocular = QPushButton("Usuń")
        btn_del_ocular.setObjectName("btn_delete")
        btn_del_ocular.setFixedWidth(54)
        btn_del_ocular.clicked.connect(self.delete_ocular_action)
        row2.addWidget(btn_del_ocular)
        layout.addLayout(row2)

        ocular_box = QFrame()
        ocular_box.setObjectName("ocular_box")
        ocular_grid = QGridLayout(ocular_box)
        ocular_grid.setContentsMargins(8, 7, 8, 7)
        ocular_grid.setSpacing(3)
        ocular_grid.addWidget(QLabel("FOV"), 0, 0)
        ocular_grid.addWidget(QLabel("Zakładka"), 1, 0)

        self.label_ocular_fov = QLabel("--- × --- mm")
        self.label_ocular_fov.setObjectName("info_val")
        self.label_ocular_overlap = QLabel("--- %")
        self.label_ocular_overlap.setObjectName("info_val")

        ocular_grid.addWidget(self.label_ocular_fov, 0, 1)
        ocular_grid.addWidget(self.label_ocular_overlap, 1, 1)
        layout.addWidget(ocular_box)

        layout.addStretch()
        return w

    def _tab_xyz(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(_section_label("Krok ruchu"))
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("Krok [mm]:"))
        self.spin_platform_step = DoubleSpinBox()
        self.spin_platform_step.setDecimals(3)
        self.spin_platform_step.setRange(0.002, 30.0)
        self.spin_platform_step.setValue(1.0)
        self.spin_platform_step.setSingleStep(0.001)
        step_row.addWidget(self.spin_platform_step)
        layout.addLayout(step_row)

        layout.addWidget(_section_label("Sterowanie"))

        dpad = QGridLayout()
        dpad.setSpacing(4)

        btn_yp = QPushButton("Y +")
        btn_yp.clicked.connect(lambda: self.validate_and_move('Y', 1))
        btn_ym = QPushButton("Y −")
        btn_ym.clicked.connect(lambda: self.validate_and_move('Y', -1))
        btn_xm = QPushButton("X −")
        btn_xm.clicked.connect(lambda: self.validate_and_move('X', -1))
        btn_xp = QPushButton("X +")
        btn_xp.clicked.connect(lambda: self.validate_and_move('X', 1))

        btn_center = QPushButton("CTR")
        btn_center.setObjectName("btn_start_live")
        btn_center.clicked.connect(self.platform_move_to_center)

        dpad.addWidget(btn_yp, 0, 1)
        dpad.addWidget(btn_xm, 1, 0)
        dpad.addWidget(btn_center, 1, 1)
        dpad.addWidget(btn_xp, 1, 2)
        dpad.addWidget(btn_ym, 2, 1)
        layout.addLayout(dpad)

        z_row = QHBoxLayout()
        btn_zm = QPushButton("Z −")
        btn_zm.clicked.connect(lambda: self.validate_and_move('Z', -1))
        btn_zp = QPushButton("Z +")
        btn_zp.clicked.connect(lambda: self.validate_and_move('Z', 1))
        z_row.addWidget(btn_zm)
        z_row.addWidget(btn_zp)
        layout.addLayout(z_row)

        layout.addWidget(_sep())

        home_row = QHBoxLayout()
        btn_home = QPushButton("Home ($H)")
        btn_home.clicked.connect(self.platform_homing)
        btn_unlock = QPushButton("Unlock ($X)")
        btn_unlock.clicked.connect(self.platform_unlock)
        home_row.addWidget(btn_home)
        home_row.addWidget(btn_unlock)
        layout.addLayout(home_row)

        layout.addWidget(_sep())
        layout.addWidget(_section_label("Aktualna pozycja"))

        self.label_pos_xyz = QLabel("X=0.00 mm   Y=0.00 mm   Z=0.00 mm")
        self.label_pos_xyz.setObjectName("pos_label_box")
        self.label_pos_xyz.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pos_xyz)

        layout.addStretch()
        return w

    def _tab_skan(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)

        layout.addWidget(_section_label("Aktywny preset"))
        active_preset_box = QFrame()
        active_preset_box.setObjectName("active_preset_box")
        ap_layout = QHBoxLayout(active_preset_box)
        ap_layout.setContentsMargins(8, 5, 8, 5)
        self.label_active_preset = QLabel("brak")
        self.label_active_preset.setObjectName("active_preset_lbl")
        ap_layout.addWidget(self.label_active_preset)
        ap_layout.addStretch()
        layout.addWidget(active_preset_box)

        layout.addWidget(_sep())

        layout.addWidget(_section_label("Focus stack"))

        grid = QGridLayout()
        grid.setSpacing(5)

        grid.addWidget(QLabel("Min Z [mm]"), 0, 0)
        self.spin_fs_min_height = DoubleSpinBox()
        self.spin_fs_min_height.setRange(0.0, 200.0)
        self.spin_fs_min_height.setValue(0.0)
        self.spin_fs_min_height.setSingleStep(0.1)
        grid.addWidget(self.spin_fs_min_height, 0, 1)

        grid.addWidget(QLabel("Max Z (obecna)"), 1, 0)
        self.spin_fs_max_height = DoubleSpinBox()
        self.spin_fs_max_height.setRange(0.0, 200.0)
        self.spin_fs_max_height.setReadOnly(True)
        self.spin_fs_max_height.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        grid.addWidget(self.spin_fs_max_height, 1, 1)

        grid.addWidget(QLabel("Ilość klatek Z"), 2, 0)
        self.spin_fs_frames = SpinBox()
        self.spin_fs_frames.setRange(2, 500)
        self.spin_fs_frames.setValue(5)
        grid.addWidget(self.spin_fs_frames, 2, 1)

        layout.addLayout(grid)

        layout.addWidget(_sep())
        layout.addWidget(_section_label("Opcje"))

        self.check_use_mapping = QCheckBox("Mapping (trasa XY)")
        self.check_use_mapping.stateChanged.connect(self.update_image_format_controls)
        layout.addWidget(self.check_use_mapping)

        self.check_use_focus_stack = QCheckBox("Focus stack")
        self.check_use_focus_stack.stateChanged.connect(self.update_image_format_controls)
        layout.addWidget(self.check_use_focus_stack)

        layout.addWidget(_sep())
        layout.addWidget(_section_label("Akcje"))

        btn_capture = QPushButton("Zrób zdjęcie")
        btn_capture.setObjectName("btn_capture")
        btn_capture.clicked.connect(self.capture_image)
        layout.addWidget(btn_capture)

        btn_scan = QPushButton("Skanuj zakres fal")
        btn_scan.setObjectName("btn_scan")
        btn_scan.clicked.connect(self.start_scan)
        layout.addWidget(btn_scan)

        layout.addStretch()
        return w

    def _tab_edytor(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)

        layout.addWidget(_section_label("Edytor presetów"))

        grid_p = QGridLayout()
        grid_p.setSpacing(5)

        grid_p.addWidget(QLabel("Nazwa"), 0, 0)
        self.edit_preset_name = QLineEdit("default")
        grid_p.addWidget(self.edit_preset_name, 0, 1)

        grid_p.addWidget(QLabel("Step [nm]"), 1, 0)
        self.combo_preset_step = QComboBox()
        self.combo_preset_step.addItems(["10", "20", "30", "40", "50"])
        self.combo_preset_step.currentTextChanged.connect(self.update_preset_constraints)
        grid_p.addWidget(self.combo_preset_step, 1, 1)

        grid_p.addWidget(QLabel("Mode"), 2, 0)
        self.combo_preset_mode = QComboBox()
        self.combo_preset_mode.addItems(list(self.bandwidth_modes.keys()))
        grid_p.addWidget(self.combo_preset_mode, 2, 1)

        grid_p.addWidget(QLabel("Start λ [nm]"), 3, 0)
        self.combo_preset_start = QComboBox()
        grid_p.addWidget(self.combo_preset_start, 3, 1)

        grid_p.addWidget(QLabel("Stop λ [nm]"), 4, 0)
        self.combo_preset_stop = QComboBox()
        grid_p.addWidget(self.combo_preset_stop, 4, 1)

        grid_p.addWidget(QLabel("Wysokość [mm]"), 5, 0)
        self.spin_preset_height = DoubleSpinBox()
        self.spin_preset_height.setRange(0.0, 200.0)
        self.spin_preset_height.setValue(10.0)
        grid_p.addWidget(self.spin_preset_height, 5, 1)

        grid_p.addWidget(QLabel("Długość [mm]"), 6, 0)
        self.spin_preset_length = DoubleSpinBox()
        self.spin_preset_length.setRange(0.0, 200.0)
        self.spin_preset_length.setValue(50.0)
        grid_p.addWidget(self.spin_preset_length, 6, 1)

        layout.addLayout(grid_p)

        btn_save_preset = QPushButton("Zapisz preset")
        btn_save_preset.setObjectName("btn_save")
        btn_save_preset.clicked.connect(self.save_preset)
        layout.addWidget(btn_save_preset)

        layout.addWidget(_sep())
        layout.addWidget(_section_label("Edytor obiektywów"))

        grid_o = QGridLayout()
        grid_o.setSpacing(5)

        grid_o.addWidget(QLabel("Nazwa"), 0, 0)
        self.edit_ocular_name = QLineEdit("Plan_Apo_10x")
        grid_o.addWidget(self.edit_ocular_name, 0, 1)

        grid_o.addWidget(QLabel("FOV X [mm]"), 1, 0)
        self.spin_fov_x = DoubleSpinBox()
        self.spin_fov_x.setRange(0.01, 200.0)
        self.spin_fov_x.setDecimals(3)
        self.spin_fov_x.setValue(2.500)
        self.spin_fov_x.setSingleStep(0.1)
        grid_o.addWidget(self.spin_fov_x, 1, 1)

        grid_o.addWidget(QLabel("FOV Y [mm]"), 2, 0)
        self.spin_fov_y = DoubleSpinBox()
        self.spin_fov_y.setRange(0.01, 200.0)
        self.spin_fov_y.setDecimals(3)
        self.spin_fov_y.setValue(1.800)
        self.spin_fov_y.setSingleStep(0.1)
        grid_o.addWidget(self.spin_fov_y, 2, 1)

        grid_o.addWidget(QLabel("Zakładka [%]"), 3, 0)
        self.spin_overlap = SpinBox()
        self.spin_overlap.setRange(0, 90)
        self.spin_overlap.setValue(15)
        grid_o.addWidget(self.spin_overlap, 3, 1)

        layout.addLayout(grid_o)

        btn_save_ocular = QPushButton("Zapisz obiektyw")
        btn_save_ocular.setObjectName("btn_save")
        btn_save_ocular.clicked.connect(self.save_ocular)
        layout.addWidget(btn_save_ocular)

        layout.addStretch()

        self.update_preset_constraints()
        return w

    # ── Logic methods ────────────────────────────────────────────

    def connect(self):
        success = self.acquisition.connect_hardware()
        if success:
            self.set_connection_status(self.cam_status_label, "Kamera", True)
            self.set_connection_status(self.kur_status_label, "KURIOS", True)

        if self.platform.connect():
            self.set_platform_status(True)
        else:
            self.set_platform_status(False)

        self.adjust_lighting()
        self._update_connection_buttons()

    def set_connection_status(self, label, name, connected):
        dot = "●"
        if self.theme == "light":
            color = "#186550" if connected else "#909498"
        else:
            color = "#2dcaa5" if connected else "#888d99"
        state = "OK" if connected else "–"
        label.setText(f"{dot} {name}: {state}")
        label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 500;"
            "padding: 0 4px; background: transparent; border: none;"
        )

    def set_platform_status(self, connected):
        self.set_connection_status(self.platform_status_label, "Platforma", connected)
        self._update_connection_buttons()

    def _update_connection_buttons(self):
        if not hasattr(self, "btn_connect"):
            return
        cam = self.acquisition.camera_connected
        kur = self.acquisition.kurios_connected
        platform_conn = False
        if self.platform.grbl.ser is not None:
            platform_conn = self.platform.is_connected()

        all_connected = cam and kur and platform_conn
        any_connected = cam or kur or platform_conn

        self.btn_connect.setEnabled(not all_connected)
        self.btn_disconnect.setEnabled(any_connected)

    def _update_live_view_buttons(self):
        self.btn_start_live.setEnabled(not self.is_live_view_running)
        self.btn_stop_live.setEnabled(self.is_live_view_running)

    def disconnect_platform_action(self):
        self.platform.force_stop_and_disconnect()
        self.set_platform_status(False)
        self.label_pwm_val.setText("PWM: 0")
        if hasattr(self, "pwm_slider"):
            self.pwm_slider.blockSignals(True)
            self.pwm_slider.setValue(0)
            self.pwm_slider.blockSignals(False)
        self._update_connection_buttons()

    def check_platform_connection(self):
        if self.platform.grbl.ser is None:
            self.set_platform_status(False)
            self._update_connection_buttons()
            return
        self.set_platform_status(self.platform.is_connected())
        self._update_connection_buttons()

    def ensure_platform_connected(self):
        if self.platform.is_connected():
            return True
        self.set_platform_status(False)
        QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!\nProszę kliknąć przycisk 'Połącz'.")
        return False

    def refresh_live_parameters(self):
        params = AcquisitionParams(
            wavelength=self.spin_wavelength.value(),
            exposure=self.spin_exposure.value(),
            gain=self.spin_gain.value(),
            bandwidth_mode=self.combo_bandwidth.currentText()
        )
        self.acquisition.set_hardware_params(params)

    def trigger_hardware_update(self):
        self.debounce_timer.start(300)

    def update_image_format_controls(self, *_):
        # Mapping (stitching) requires multi-page TIFF; focus stack alone can save in PNG/JPG.
        if self.check_use_mapping.isChecked():
            self.combo_image_format.setCurrentText(".tiff")
            self.combo_image_format.setEnabled(False)
        else:
            self.combo_image_format.setEnabled(True)

    def _force_tiff_output(self):
        self.combo_image_format.setCurrentText(".tiff")
        return ".tiff"

    def _get_focus_stack_params(self):
        if not self.check_use_focus_stack.isChecked():
            return None
        return {
            "bottom_height": self.spin_fs_min_height.value(),
            "top_height": self.spin_fs_max_height.value(),
            "num_frames": self.spin_fs_frames.value()
        }

    def _get_selected_sample_geometry(self):
        selected_preset = self.combo_select_preset.currentText()
        preset_data = self.presets.get_preset_data(selected_preset)
        if not preset_data:
            QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu próbki!")
            return None
        if not self.preset_fov_x or not self.preset_fov_y:
            QMessageBox.warning(self, "Błąd", "Nie wybrano obiektywu do mapowania!")
            return None
        if not self.platform.is_connected():
            self.set_platform_status(False)
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!")
            return None
        if not self.platform.is_ready:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest gotowa. Wykonaj Homing lub Unlock.")
            return None
        return {
            "sample_width": preset_data.get("sample_length", 10.0),
            "sample_height": preset_data.get("sample_height", 10.0),
            "fov_x": self.preset_fov_x,
            "fov_y": self.preset_fov_y,
            "overlap": self.preset_overlap
        }

    def _ensure_platform_for_focus_stack(self):
        if self.check_use_focus_stack.isChecked() and not self.platform.is_connected():
            self.set_platform_status(False)
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona. Kliknij 'Połącz' przed focus stackingiem.")
            return False
        if self.check_use_focus_stack.isChecked() and not self.platform.is_ready:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest gotowa. Wykonaj Homing lub Unlock przed focus stackingiem.")
            return False
        return True

    def _update_position_label_queued(self):
        pos_text = (
            f"Aktualna pozycja:  X={self.platform.x_state:.2f} mm  "
            f"Y={self.platform.y_state:.2f} mm  Z={self.platform.z_state:.2f} mm"
        )
        QMetaObject.invokeMethod(
            self.label_pos, "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, pos_text)
        )
        QMetaObject.invokeMethod(
            self.label_pos_xyz, "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, f"X={self.platform.x_state:.2f} mm   Y={self.platform.y_state:.2f} mm   Z={self.platform.z_state:.2f} mm")
        )

    def _get_acquisition_geometry_if_needed(self):
        if not self.check_use_mapping.isChecked():
            return {}
        geometry = self._get_selected_sample_geometry()
        return geometry or None

    def _run_acquisition_thread(self, params: AcquisitionParams):
        def run_thread():
            self.acquisition.run_acquisition(
                platform=self.platform,
                params=params
            )
            self._update_position_label_queued()

        acquisition_thread = threading.Thread(target=run_thread, daemon=True)
        acquisition_thread.start()

    def capture_image(self):

        if self.acquisition.camera_connected and self.acquisition.camera.is_live:
            self.stop_live_view_action()

        if not self._ensure_platform_for_focus_stack():
            return

        # Mapping (stitching) requires TIFF tiles; focus-stack alone keeps user-chosen format.
        if self.check_use_mapping.isChecked():
            image_format = self._force_tiff_output()
        else:
            image_format = self.combo_image_format.currentText()
        focus_stack_params = self._get_focus_stack_params()
        geometry = self._get_acquisition_geometry_if_needed()
        if geometry is None:
            return
        bandwidth_name = self.combo_bandwidth.currentText()

        params = AcquisitionParams(
            save_path=self.save_path,
            image_format=image_format,
            wavelength=self.spin_wavelength.value(),
            exposure=self.spin_exposure.value(),
            gain=self.spin_gain.value(),
            bandwidth_mode=bandwidth_name,
            bandwidth_code=self.bandwidth_modes.get(bandwidth_name, 4),
            spectral_scan=False,
            mapping=self.check_use_mapping.isChecked(),
            focus_stack_params=focus_stack_params,
            **(geometry if geometry else {})
        )
        self._run_acquisition_thread(params)

    def start_scan(self):
        if not self.preset_start_wavelength:
            QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu skanowania!")
            return

        if self.acquisition.camera_connected and self.acquisition.camera.is_live:
            self.stop_live_view_action()

        if not self._ensure_platform_for_focus_stack():
            return
        image_format = self._force_tiff_output()
        focus_stack_params = self._get_focus_stack_params()
        geometry = self._get_acquisition_geometry_if_needed()
        if geometry is None:
            return

        params = AcquisitionParams(
            save_path=self.save_path,
            image_format=image_format,
            spectral_scan=True,
            wavelength=self.spin_wavelength.value(),
            starting_wavelength=self.preset_start_wavelength,
            ending_wavelength=self.preset_end_wavelength,
            step=self.preset_step,
            bandwidth_mode=self.preset_mode,
            gain=self.spin_gain.value(),
            exposure=self.spin_exposure.value(),
            mapping=self.check_use_mapping.isChecked(),
            focus_stack_params=focus_stack_params,
            **(geometry if geometry else {})
        )
        self._run_acquisition_thread(params)

    def select_save_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder do zapisu", self.save_path)
        if directory:
            self.save_path = directory
            self.edit_save_path.setText(self.save_path)

    def validate_and_move(self, axis, direction):
        if not self.ensure_platform_connected():
            return
        if not self.platform.is_ready:
            QMessageBox.warning(self, "Blokada Platformy",
                "Platforma jest zablokowana (stan Alarm).\n"
                "Proszę wykonać Homing ($H) lub Unlock ($X), aby umożliwić ruch.")
            return
        step = self.spin_platform_step.value()
        if self.platform.validate_and_move(axis, step, direction) == False:
            QMessageBox.warning(self, "Ostrzeżenie",
                f"Ruch o {step * direction} mm w osi {axis} przekracza zakres platformy!")
        else:
            self.update_position_label()

    def update_position_label(self):
        x, y, z = self.platform.x_state, self.platform.y_state, self.platform.z_state
        self.label_pos.setText(
            f"Aktualna pozycja:  X={x:.2f} mm  Y={y:.2f} mm  Z={z:.2f} mm"
        )
        self.label_pos_xyz.setText(f"X={x:.2f} mm   Y={y:.2f} mm   Z={z:.2f} mm")
        if hasattr(self, 'spin_fs_max_height'):
            self.spin_fs_max_height.setValue(z)

    def platform_homing(self):
        if not self.ensure_platform_connected():
            return

        # Stop the periodic connection-check timer: it acquires the same serial
        # lock as homing and would block the Qt main thread for the full homing
        # duration (up to 120 s) if left running.
        self.platform_connection_timer.stop()

        def _do_homing():
            self.platform.homing()
            # Hand control back to the Qt main thread when done.
            QTimer.singleShot(0, self._on_homing_complete)

        threading.Thread(target=_do_homing, daemon=True).start()

    def _on_homing_complete(self):
        """Called on the Qt main thread after the homing thread finishes."""
        self.update_position_label()
        self.platform_connection_timer.start(2000)

    def platform_unlock(self):
        if not self.ensure_platform_connected():
            return
        self.platform.unlock()

    def platform_move_to_center(self):
        if not self.ensure_platform_connected():
            return
        if not self.platform.is_ready:
            QMessageBox.warning(self, "Blokada Platformy",
                "Platforma jest zablokowana. Wykonaj Homing ($H) lub Unlock ($X).")
            return
        self.platform.move_to_center()
        self.update_position_label()

    def adjust_lighting(self):
        val = self.pwm_slider.value()
        self.label_pwm_val.setText(f"{val} / 255")
        self.pwm_controller.set_pwm(val)

    def open_settings(self):
        dlg = AdvancedSettingsDialog(
            self, self.platform, self.pwm_controller,
            theme=self.theme, on_theme_change=self.set_theme,
        )
        dlg.exec()

    def update_preset_constraints(self):
        step_text = self.combo_preset_step.currentText()
        if not step_text:
            return
        step = int(step_text)
        min_val = 450
        max_val = 690 if step in [20, 30, 40] else 700
        valid_values_str = [str(x) for x in range(min_val, max_val + 1, step)]

        current_start = self.combo_preset_start.currentText()
        self.combo_preset_start.blockSignals(True)
        self.combo_preset_start.clear()
        self.combo_preset_start.addItems(valid_values_str)
        if current_start in valid_values_str:
            self.combo_preset_start.setCurrentText(current_start)
        else:
            self.combo_preset_start.setCurrentIndex(0)
        self.combo_preset_start.blockSignals(False)

        current_stop = self.combo_preset_stop.currentText()
        self.combo_preset_stop.blockSignals(True)
        self.combo_preset_stop.clear()
        self.combo_preset_stop.addItems(valid_values_str)
        if current_stop in valid_values_str:
            self.combo_preset_stop.setCurrentText(current_stop)
        else:
            self.combo_preset_stop.setCurrentIndex(len(valid_values_str) - 1)
        self.combo_preset_stop.blockSignals(False)

    def save_preset(self):
        name = self.edit_preset_name.text()
        if not name:
            print("[INFO] Błąd: Podaj nazwę presetu!")
            return
        try:
            start_val = int(self.combo_preset_start.currentText())
            end_val = int(self.combo_preset_stop.currentText())
            step_val = int(self.combo_preset_step.currentText())
        except ValueError:
            print("[INFO] Błąd wartości numerycznych w presecie!")
            return
        preset_data = {
            "mode": self.combo_preset_mode.currentText(),
            "start_wavelength": start_val,
            "end_wavelength": end_val,
            "step": step_val,
            "sample_height": self.spin_preset_height.value(),
            "sample_length": self.spin_preset_length.value()
        }
        self.presets.save_new_preset(name, preset_data)
        updated_names = list(self.presets.get_preset_names())
        self.combo_select_preset.clear()
        self.combo_select_preset.addItem("Wybierz preset")
        self.combo_select_preset.addItems(updated_names)
        self.combo_select_preset.setCurrentText(name)

    def delete_preset_action(self):
        selected_name = self.combo_select_preset.currentText()
        if not selected_name or selected_name == "Wybierz preset":
            return
        reply = QMessageBox.question(self, "Usuwanie presetu",
            f"Czy na pewno chcesz usunąć preset '{selected_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.presets.delete_preset(selected_name)
            updated_names = list(self.presets.get_preset_names())
            self.combo_select_preset.blockSignals(True)
            self.combo_select_preset.clear()
            self.combo_select_preset.addItem("Wybierz preset")
            self.combo_select_preset.addItems(updated_names)
            self.combo_select_preset.blockSignals(False)
            if updated_names:
                self.combo_select_preset.setCurrentIndex(1)
                self.on_preset_selected(self.combo_select_preset.currentText())
            else:
                self.label_mode.setText("---")
                self.label_range.setText("---")
                self.label_step.setText("---")
                self.label_geo.setText("---")
                self.preset_name = None
                self.preset_start_wavelength = None
                if hasattr(self, "label_active_preset"):
                    self.label_active_preset.setText("brak")

    def save_ocular(self):
        name = self.edit_ocular_name.text()
        if not name:
            print("[INFO] Błąd: Podaj nazwę obiektywu!")
            return
        ocular_data = {
            "fov_x_mm": self.spin_fov_x.value(),
            "fov_y_mm": self.spin_fov_y.value(),
            "overlap_percent": self.spin_overlap.value()
        }
        self.oculars.save_new_preset(name, ocular_data)
        updated_names = list(self.oculars.get_preset_names())
        self.combo_select_ocular.blockSignals(True)
        self.combo_select_ocular.clear()
        self.combo_select_ocular.addItem("Wybierz obiektyw")
        self.combo_select_ocular.addItems(updated_names)
        self.combo_select_ocular.blockSignals(False)
        self.combo_select_ocular.setCurrentText(name)

    def delete_ocular_action(self):
        selected_name = self.combo_select_ocular.currentText()
        if not selected_name or selected_name == "Wybierz obiektyw":
            return
        reply = QMessageBox.question(self, "Usuwanie obiektywu",
            f"Czy na pewno chcesz usunąć obiektyw '{selected_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.oculars.delete_preset(selected_name)
            updated_names = list(self.oculars.get_preset_names())
            self.combo_select_ocular.blockSignals(True)
            self.combo_select_ocular.clear()
            self.combo_select_ocular.addItem("Wybierz obiektyw")
            self.combo_select_ocular.addItems(updated_names)
            self.combo_select_ocular.blockSignals(False)
            self.combo_select_ocular.setCurrentIndex(0)
            self.on_ocular_selected("Wybierz obiektyw")

    def on_ocular_selected(self, text):
        if text == "Wybierz obiektyw" or not text:
            self.label_ocular_fov.setText("--- × --- mm")
            self.label_ocular_overlap.setText("--- %")
            self.preset_fov_x = None
            self.preset_fov_y = None
            self.preset_overlap = None
            return
        ocular_data = self.oculars.get_preset_data(text)
        if ocular_data:
            self.preset_fov_x = ocular_data.get("fov_x_mm", 0.0)
            self.preset_fov_y = ocular_data.get("fov_y_mm", 0.0)
            self.preset_overlap = ocular_data.get("overlap_percent", 0)
            self.label_ocular_fov.setText(f"{self.preset_fov_x} × {self.preset_fov_y} mm")
            self.label_ocular_overlap.setText(f"{self.preset_overlap} %")
            print(f"[INFO] Załadowano obiektyw '{text}'.")

    def start_live_view_action(self):
        if not self.acquisition.camera_connected and not self.acquisition.kurios_connected:
            print("[INFO] Najpierw połącz kamerę!")
            return
        self.refresh_live_parameters()
        queue = self.acquisition.start_live_view()
        if queue:
            self.live_view_widget.start_live_view(queue)
            self.is_live_view_running = True
            self._update_live_view_buttons()

    def stop_live_view_action(self):
        self.live_view_widget.stop_live_view()
        self.acquisition.stop_live_view()
        self.is_live_view_running = False
        self._update_live_view_buttons()

    def on_preset_selected(self, text):
        if text == "Wybierz preset" or not text:
            self.label_mode.setText("---")
            self.label_range.setText("---")
            self.label_step.setText("---")
            self.label_geo.setText("---")
            self.preset_name = None
            self.preset_mode = None
            self.preset_start_wavelength = None
            self.preset_end_wavelength = None
            self.preset_step = None
            if hasattr(self, "label_active_preset"):
                self.label_active_preset.setText("brak")
            return
        preset_data = self.presets.get_preset_data(text)
        if preset_data:
            p_mode = preset_data.get("mode", "Wide")
            p_start = preset_data.get("start_wavelength", 500)
            p_end = preset_data.get("end_wavelength", 600)
            p_step = preset_data.get("step", 10)
            p_height = preset_data.get("sample_height", 0.0)
            p_length = preset_data.get("sample_length", 0.0)
            self.preset_name = text
            self.preset_mode = p_mode
            self.preset_start_wavelength = p_start
            self.preset_end_wavelength = p_end
            self.preset_step = p_step
            self.label_mode.setText(p_mode)
            self.label_range.setText(f"{p_start} – {p_end} nm")
            self.label_step.setText(f"{p_step} nm")
            self.label_geo.setText(f"H={p_height}mm  L={p_length}mm")
            if hasattr(self, "label_active_preset"):
                self.label_active_preset.setText(text)
            print(f"[INFO] Załadowano preset '{text}'.")

    def on_close(self, event=None):
        print("[INFO] Zamykanie aplikacji i zwalnianie zasobów...")
        if hasattr(self, 'platform_connection_timer'):
            self.platform_connection_timer.stop()
        if hasattr(self, 'acquisition'):
            self.acquisition.cleanup()
        if hasattr(self, 'pwm_controller'):
            self.pwm_controller.set_pwm(0)
            self.pwm_controller.close()
        if hasattr(self, 'platform'):
            self.platform.disconnect()
        if event:
            event.accept()
        else:
            self.close()

    def closeEvent(self, event):
        self.on_close(event)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
