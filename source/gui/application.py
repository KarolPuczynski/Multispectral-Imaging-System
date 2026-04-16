import sys
import os
import threading
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer

from core.acquisition import Acquisition
from core.preset_handling import PresetManager
from hardware.move_platform import Platform
from hardware.led_controller import LedController
from gui.live_view import LiveViewWidget
from gui.advanced_mode import AdvancedSettingsDialog

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multispectral System")

        self.save_path = os.getcwd()

        self.init_logic_modules()
        self.init_ui()

        self.preset_name = None
        self.preset_mode = None
        self.preset_start_wavelength = None
        self.preset_end_wavelength = None
        self.preset_step = None

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.refresh_live_parameters)


    def init_logic_modules(self):
        self.acquisition = Acquisition()
        self.presets = PresetManager("presets.json")
        self.platform = Platform()
        self.pwm_controller = LedController(port="COM6")
        self.bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)
        
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 4)
        main_layout.setColumnStretch(2, 1)

        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 0, 0)

        middle_panel = self.create_middle_panel()
        main_layout.addWidget(middle_panel, 0, 1)

        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 0, 2)

    def create_left_panel(self):
        group_box = QGroupBox("Urządzenia & akwizycja")
        layout = QVBoxLayout()

        # Przyciski sterujące
        buttons = {
            "Połącz": self.connect,
            "Zrób zdjęcie": self.capture_image,
            "Skanuj zakres": self.start_scan,
            "Ustawienia / Konsola": self.open_settings,
            "Zakończ": self.on_close
        }

        for text, command in buttons.items():
            btn = QPushButton(text)
            btn.clicked.connect(command)
            layout.addWidget(btn)

        # Statusy polaczania kamery i filtra
        self.cam_status_label = QLabel("Kamera: Rozłączona")
        self.cam_status_label.setStyleSheet("color: red")
        layout.addWidget(self.cam_status_label)

        self.kur_status_label = QLabel("KURIOS: Rozłączony")
        self.kur_status_label.setStyleSheet("color: red")
        layout.addWidget(self.kur_status_label)

        self.platform_status_label = QLabel("Platforma: Rozłączona")
        self.platform_status_label.setStyleSheet("color: red")
        layout.addWidget(self.platform_status_label)

        self.pwm_status_label = QLabel("PWM: Rozłączony")
        self.pwm_status_label.setStyleSheet("color: red")
        layout.addWidget(self.pwm_status_label)

        layout.addWidget(self._create_manual_controls())

        layout.addWidget(self._create_save_path_controls())

        layout.addWidget(self._create_platform_controls())
        layout.addWidget(self._create_pwm_controls())

        layout.addStretch() 
        group_box.setLayout(layout)
        return group_box

    def _create_manual_controls(self):
        group = QGroupBox("Parametry zdjęcia (manualne)")
        layout = QGridLayout()

        layout.addWidget(QLabel("λ [nm]"), 0, 0)
        self.spin_wavelength = QSpinBox()
        self.spin_wavelength.setRange(450, 700)
        self.spin_wavelength.setValue(500)
        self.spin_wavelength.valueChanged.connect(self.trigger_hardware_update)
        layout.addWidget(self.spin_wavelength, 0, 1)

        layout.addWidget(QLabel("Ekspozycja [µs]"), 1, 0)
        self.spin_exposure = QSpinBox()
        self.spin_exposure.setRange(100, 59269000) # range of exposure times for CS135MU camera [us]
        self.spin_exposure.setValue(50000)
        self.spin_exposure.valueChanged.connect(self.trigger_hardware_update)
        layout.addWidget(self.spin_exposure, 1, 1)

        layout.addWidget(QLabel("Gain"), 2, 0)
        self.spin_gain = QDoubleSpinBox()
        self.spin_gain.setRange(0.0, 48.0) # range of gain for CS135MU camera
        self.spin_gain.setSingleStep(0.1) 
        self.spin_gain.setValue(0.0)
        self.spin_gain.valueChanged.connect(self.trigger_hardware_update)
        layout.addWidget(self.spin_gain, 2, 1)

        self.combo_bandwidth = QComboBox()
        self.combo_bandwidth.addItems(list(self.bandwidth_modes.keys()))
        self.combo_bandwidth.currentTextChanged.connect(self.trigger_hardware_update)
        layout.addWidget(QLabel("Tryb pasma"), 3, 0)
        layout.addWidget(self.combo_bandwidth, 3, 1)

        group.setLayout(layout)
        return group

    def _create_save_path_controls(self):
        self.image_formats = (".tiff", ".png", ".jpg")

        group = QGroupBox("Ścieżka zapisu")
        layout = QGridLayout()

        self.edit_save_path = QLineEdit(self.save_path)
        self.edit_save_path.setReadOnly(True)
        layout.addWidget(self.edit_save_path, 0, 0)

        btn_select_path = QPushButton("Wybierz...")
        btn_select_path.clicked.connect(self.select_save_directory)
        layout.addWidget(btn_select_path, 0, 1)

        self.combo_image_format = QComboBox()
        self.combo_image_format.addItems(self.image_formats)
        layout.addWidget(QLabel("Format zapisu"), 1, 0)
        layout.addWidget(self.combo_image_format, 1, 1)

        group.setLayout(layout)
        return group

    def _create_platform_controls(self):
        group = QGroupBox("Sterowanie platformą (XYZ)")
        layout = QGridLayout()

        # Pole tekstowe na krok
        layout.addWidget(QLabel("Krok [mm]:"), 0, 0)
        self.spin_platform_step = QDoubleSpinBox()
        self.spin_platform_step.setRange(0.01, 30.0)
        self.spin_platform_step.setValue(1.0)
        self.spin_platform_step.setSingleStep(0.1)
        layout.addWidget(self.spin_platform_step, 0, 1)

        # Oś X
        btn_xm = QPushButton("X -")
        btn_xm.clicked.connect(lambda: self.validate_and_move('X', -1))
        layout.addWidget(btn_xm, 1, 0)
        
        btn_xp = QPushButton("X +")
        btn_xp.clicked.connect(lambda: self.validate_and_move('X', 1))
        layout.addWidget(btn_xp, 1, 1)

        # Oś Y
        btn_ym = QPushButton("Y -")
        btn_ym.clicked.connect(lambda: self.validate_and_move('Y', -1))
        layout.addWidget(btn_ym, 2, 0)
        
        btn_yp = QPushButton("Y +")
        btn_yp.clicked.connect(lambda: self.validate_and_move('Y', 1))
        layout.addWidget(btn_yp, 2, 1)

        # Oś Z
        btn_zm = QPushButton("Z -")
        btn_zm.clicked.connect(lambda: self.validate_and_move('Z', -1))
        layout.addWidget(btn_zm, 3, 0)
        
        btn_zp = QPushButton("Z +")
        btn_zp.clicked.connect(lambda: self.validate_and_move('Z', 1))
        layout.addWidget(btn_zp, 3, 1)

        # Homing / Unlock
        btn_home = QPushButton("Home ($H)")
        btn_home.clicked.connect(self.platform_homing)
        layout.addWidget(btn_home, 4, 0)
        
        btn_unlock = QPushButton("Unlock ($X)")
        btn_unlock.clicked.connect(self.platform_unlock)
        layout.addWidget(btn_unlock, 4, 1)

        # Wyświetlanie aktualnej pozycji
        self.label_pos = QLabel("Pozycja: X=0.00, Y=0.00, Z=0.00")
        self.label_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pos, 5, 0, 1, 2)

        group.setLayout(layout)
        return group

    def _create_pwm_controls(self):
        group = QGroupBox("Oświetlenie (PWM)")
        layout = QVBoxLayout()

        self.pwm_slider = QSlider(Qt.Orientation.Horizontal)
        self.pwm_slider.setRange(0, 255)
        self.pwm_slider.setValue(128)
        self.pwm_slider.valueChanged.connect(self.adjust_lighting) # wywołuje przy ruchu
        layout.addWidget(self.pwm_slider)

        self.label_pwm_val = QLabel("PWM: 128")
        self.label_pwm_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pwm_val)

        group.setLayout(layout)
        return group

    def create_middle_panel(self):
        group = QGroupBox("Podgląd i Preset")
        layout = QVBoxLayout()

        # LIVE VIEW
        # Kontener na obraz z kamery
        self.live_view_widget = LiveViewWidget()
        layout.addWidget(self.live_view_widget, stretch=1)

        live_layout = QHBoxLayout()
        self.btn_start_live = QPushButton("Start Live View")
        self.btn_start_live.clicked.connect(self.start_live_view_action)
        live_layout.addWidget(self.btn_start_live)

        self.btn_stop_live = QPushButton("Stop Live View")
        self.btn_stop_live.clicked.connect(self.stop_live_view_action)
        self.btn_stop_live.setEnabled(False)
        live_layout.addWidget(self.btn_stop_live)

        layout.addLayout(live_layout)

        # PRESETY
        # Separator wizualny
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # Wybór presetu
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Wybierz preset:"))
        
        self.combo_select_preset = QComboBox()
        self.combo_select_preset.addItems(list(self.presets.get_preset_names()))
        self.combo_select_preset.currentTextChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.combo_select_preset)
        
        btn_delete = QPushButton("Usuń")
        btn_delete.clicked.connect(self.delete_preset_action)
        preset_layout.addWidget(btn_delete)
        
        layout.addLayout(preset_layout)

        self.label_mode = QLabel("Mode: ---")
        layout.addWidget(self.label_mode)

        self.label_range = QLabel("Zakres λ: ---")
        layout.addWidget(self.label_range)

        self.label_step = QLabel("Step: ---")
        layout.addWidget(self.label_step)

        self.label_geo = QLabel("Geometry: ---")
        layout.addWidget(self.label_geo)

        group.setLayout(layout)
        return group
 
    def create_right_panel(self):
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Edytor presetów")
        layout = QGridLayout()

        layout.addWidget(QLabel("Nazwa presetu"), 0, 0)
        self.edit_preset_name = QLineEdit("default")
        layout.addWidget(self.edit_preset_name, 0, 1)

        # Krok jako pierwszy parametr decydujący
        layout.addWidget(QLabel("Step [nm]"), 1, 0)
        self.combo_preset_step = QComboBox()
        self.combo_preset_step.addItems(["10", "20", "30", "40", "50"])
        self.combo_preset_step.currentTextChanged.connect(self.update_preset_constraints)
        layout.addWidget(self.combo_preset_step, 1, 1)

        layout.addWidget(QLabel("Mode"), 2, 0)
        self.combo_preset_mode = QComboBox()
        self.combo_preset_mode.addItems(list(self.bandwidth_modes.keys()))
        layout.addWidget(self.combo_preset_mode, 2, 1)

        # Start i Stop jako listy rozwijane, wypełniane dynamicznie
        layout.addWidget(QLabel("Start λ [nm]"), 3, 0)
        self.combo_preset_start = QComboBox()
        layout.addWidget(self.combo_preset_start, 3, 1)

        layout.addWidget(QLabel("Stop λ [nm]"), 4, 0)
        self.combo_preset_stop = QComboBox()
        layout.addWidget(self.combo_preset_stop, 4, 1)

        layout.addWidget(QLabel("Wysokość [mm]"), 5, 0)
        self.spin_preset_height = QDoubleSpinBox()
        self.spin_preset_height.setRange(0.0, 200.0)
        self.spin_preset_height.setValue(10.0)
        layout.addWidget(self.spin_preset_height, 5, 1)

        layout.addWidget(QLabel("Długość [mm]"), 6, 0)
        self.spin_preset_length = QDoubleSpinBox()
        self.spin_preset_length.setRange(0.0, 200.0)
        self.spin_preset_length.setValue(50.0)
        layout.addWidget(self.spin_preset_length, 6, 1)

        btn_save = QPushButton("Zapisz preset")
        btn_save.clicked.connect(self.save_preset)
        layout.addWidget(btn_save, 7, 0, 1, 2) # span 2 columns

        layout.setRowStretch(8, 1) # push up
        group.setLayout(layout)
        
        # Inicjalizacja ograniczeń dla domyślnego kroku (10)
        self.update_preset_constraints()
        
        panel_layout.addWidget(group)

        fs_group = QGroupBox("Focus Stacking")
        fs_layout = QGridLayout()

        fs_layout.addWidget(QLabel("Min. wysokość Z [mm]"), 0, 0)
        self.spin_fs_min_height = QDoubleSpinBox()
        self.spin_fs_min_height.setRange(0.0, 200.0)
        self.spin_fs_min_height.setValue(0.0)
        self.spin_fs_min_height.setSingleStep(0.1)
        fs_layout.addWidget(self.spin_fs_min_height, 0, 1)

        fs_layout.addWidget(QLabel("Maks. wysokość (obecna) [mm]"), 1, 0)
        self.spin_fs_max_height = QDoubleSpinBox()
        self.spin_fs_max_height.setRange(0.0, 200.0)
        self.spin_fs_max_height.setReadOnly(True)
        self.spin_fs_max_height.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        fs_layout.addWidget(self.spin_fs_max_height, 1, 1)

        fs_layout.addWidget(QLabel("Ilość zdjęć"), 2, 0)
        self.spin_fs_frames = QSpinBox()
        self.spin_fs_frames.setRange(2, 500)
        self.spin_fs_frames.setValue(5)
        fs_layout.addWidget(self.spin_fs_frames, 2, 1)

        self.check_fs_hypercube = QCheckBox("Wykonaj Hypercube scan")
        self.check_fs_hypercube.stateChanged.connect(self.toggle_fs_preset)
        fs_layout.addWidget(self.check_fs_hypercube, 3, 0, 1, 2)

        self.label_fs_preset = QLabel("Wybierz preset:")
        self.label_fs_preset.setEnabled(False)
        fs_layout.addWidget(self.label_fs_preset, 4, 0)

        self.combo_fs_preset = QComboBox()
        self.combo_fs_preset.addItems(list(self.presets.get_preset_names()))
        self.combo_fs_preset.setEnabled(False)
        fs_layout.addWidget(self.combo_fs_preset, 4, 1)

        btn_run_fs = QPushButton("Rozpocznij Focus Stacking")
        btn_run_fs.clicked.connect(self.run_focus_stacking)
        fs_layout.addWidget(btn_run_fs, 5, 0, 1, 2)

        fs_group.setLayout(fs_layout)
        panel_layout.addWidget(fs_group)
        
        panel_layout.addStretch()

        return panel_widget

    # Buttons handling

    # Łączenie się z kamera i filtrem przestrajalnym
    def connect(self):
        success = self.acquisition.connect_hardware()
        if success:
            self.cam_status_label.setText("Kamera: POŁĄCZONA")
            self.cam_status_label.setStyleSheet("color: green")

            self.kur_status_label.setText("KURIOS: POŁĄCZONY")
            self.kur_status_label.setStyleSheet("color: green")
        
        self.platform.connect()
        if self.platform.grbl.ser and self.platform.grbl.ser.is_open:
            self.platform_status_label.setText("Platforma: POŁĄCZONA")
            self.platform_status_label.setStyleSheet("color: green")

        self.pwm_controller.connect()
        if self.pwm_controller.connected:
            self.pwm_status_label.setText("PWM: POŁĄCZONY")
            self.pwm_status_label.setStyleSheet("color: green")
        
        self.adjust_lighting()

    # przechwytywanie zdjecia z manulnymi parametrami
    def capture_image(self):
        if self.acquisition.camera_connected and self.acquisition.camera.is_live:
            print("[INFO] Zatrzymywanie Live View przed wykonaniem zdjęcia...")
            self.stop_live_view_action()

        image_format = self.combo_image_format.currentText()
        wavelength = self.spin_wavelength.value()
        exposure_time = self.spin_exposure.value()
        gain = self.spin_gain.value()
        bandwidth_name = self.combo_bandwidth.currentText()
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)

        self.acquisition.capture_image(wavelength, exposure_time, gain, bandwidth_name, bandwidth_code, self.save_path, image_format)

    def refresh_live_parameters(self):
        wavelength = self.spin_wavelength.value()
        exposure = self.spin_exposure.value()
        gain = self.spin_gain.value()
        bandwidth_name = self.combo_bandwidth.currentText()

        self.acquisition.set_hardware_params(wavelength, exposure, bandwidth_name, gain)

    def trigger_hardware_update(self):
        self.debounce_timer.start(300)

    def start_scan(self):
        if not self.preset_start_wavelength:
            QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu!")
            return
            
        if self.acquisition.camera_connected and self.acquisition.camera.is_live:
            print("[INFO] Zatrzymywanie Live View przed rozpoczęciem skanowania...")
            self.stop_live_view_action()

        image_format = self.combo_image_format.currentText()
        start_wavelength = self.preset_start_wavelength
        stop_wavelength = self.preset_end_wavelength
        step = self.preset_step
        mode = self.preset_mode
        gain = self.spin_gain.value()

        def run_thread():
            self.acquisition.hypercube_scan(start_wavelength, stop_wavelength, step, mode, gain, self.save_path, image_format)

        scan_thread = threading.Thread(target=run_thread)
        scan_thread.daemon = True
        scan_thread.start()

    def select_save_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder do zapisu", self.save_path)
        if directory:
            self.save_path = directory
            self.edit_save_path.setText(self.save_path)

    def validate_and_move(self, axis, direction):
        if not self.platform.grbl.ser or not self.platform.grbl.ser.is_open:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!\nProszę kliknąć przycisk 'Połącz'.")
            return

        if not self.platform.is_ready:
            QMessageBox.warning(self, "Blokada Platformy", "Platforma jest zablokowana (stan Alarm).\nProszę wykonać Homing ($H) lub Unlock ($X), aby umożliwić ruch.")
            return

        step = self.spin_platform_step.value()

        if self.platform.validate_and_move(axis, step, direction) == False:
            QMessageBox.warning(self, "Ostrzeżenie", f"Ruch o {step * direction} mm w osi {axis} przekracza zakres platformy!")
        else:
            self.update_position_label()
            
    def update_position_label(self):
        x, y, z = self.platform.x_state, self.platform.y_state, self.platform.z_state
        self.label_pos.setText(f"Pozycja: X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
        if hasattr(self, 'spin_fs_max_height'):
            self.spin_fs_max_height.setValue(z)

    # homing platformy 
    def platform_homing(self):
        if not self.platform.grbl.ser or not self.platform.grbl.ser.is_open:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!\nProszę kliknąć przycisk 'Połącz'.")
            return

        self.platform.homing()
        self.update_position_label()

    # Odblokowanie platformy (domyslnie po wlaczeniu jest zablokowana, i wtedy można tylko ja homingowac)
    def platform_unlock(self):
        if not self.platform.grbl.ser or not self.platform.grbl.ser.is_open:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!\nProszę kliknąć przycisk 'Połącz'.")
            return

        self.platform.unlock()

    # regulacja oswietleenia probki
    def adjust_lighting(self):
        val = self.pwm_slider.value()
        self.label_pwm_val.setText(f"PWM: {val}")
        self.pwm_controller.set_pwm(val)

    def open_settings(self):
        dlg = AdvancedSettingsDialog(self, self.platform, self.pwm_controller)
        dlg.exec()

    def update_preset_constraints(self):
        step_text = self.combo_preset_step.currentText()
        if not step_text:
            return
        step = int(step_text)

        min_val = 450
        if step in [20, 30, 40]:
            max_val = 690
        else:
            max_val = 700

        valid_values = list(range(min_val, max_val + 1, step))
        valid_values_str = [str(x) for x in valid_values]

        current_start = self.combo_preset_start.currentText()
        self.combo_preset_start.blockSignals(True)
        self.combo_preset_start.clear()
        self.combo_preset_start.addItems(valid_values_str)
        if current_start in valid_values_str:
            self.combo_preset_start.setCurrentText(current_start)
        else:
            self.combo_preset_start.setCurrentIndex(0) 
        self.combo_preset_start.blockSignals(False)

        # Aktualizacja listy Stop
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
        self.combo_select_preset.addItems(updated_names)

    def delete_preset_action(self):
        selected_name = self.combo_select_preset.currentText()
        if not selected_name:
            return

        reply = QMessageBox.question(self, "Usuwanie presetu", 
                                     f"Czy na pewno chcesz usunąć preset '{selected_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.presets.delete_preset(selected_name)
            
            # Odświeżamy listę w GUI
            updated_names = list(self.presets.get_preset_names())
            self.combo_select_preset.blockSignals(True)
            self.combo_select_preset.clear()
            self.combo_select_preset.addItems(updated_names)
            self.combo_select_preset.blockSignals(False)
            
            if updated_names:
                self.combo_select_preset.setCurrentIndex(0)
                self.on_preset_selected(self.combo_select_preset.currentText())
            else:
                self.label_mode.setText("Mode: ---")
                self.label_range.setText("Zakres λ: ---")
                self.label_step.setText("Step: ---")
                self.label_geo.setText("Geometry: ---")
                self.preset_name = None
                self.preset_start_wavelength = None

    def start_live_view_action(self):
        if not self.acquisition.camera_connected and not self.acquisition.kurios_connected:
            print("[INFO] Najpierw połącz kamerę!")
            return

        self.refresh_live_parameters()
        
        queue = self.acquisition.start_live_view()
        if queue:
            self.live_view_widget.start_live_view(queue)
            self.btn_start_live.setEnabled(False)
            self.btn_stop_live.setEnabled(True)

    def stop_live_view_action(self):
        self.live_view_widget.stop_live_view()
        self.acquisition.stop_live_view()
        self.btn_start_live.setEnabled(True)
        self.btn_stop_live.setEnabled(False)

    def on_preset_selected(self, text):
        selected_name = text

        preset_data = self.presets.get_preset_data(selected_name)

        if preset_data:
            p_mode = preset_data.get("mode", "Wide")
            p_start = preset_data.get("start_wavelength", 500)
            p_end = preset_data.get("end_wavelength", 600)
            p_step = preset_data.get("step", 10)
            p_height = preset_data.get("sample_height", 0.0)
            p_length = preset_data.get("sample_length", 0.0)

            self.preset_mode = p_mode
            self.preset_start_wavelength = p_start
            self.preset_end_wavelength = p_end
            self.preset_step = p_step

            self.label_mode.setText(f"Mode: {p_mode}")
            self.label_range.setText(f"Zakres λ: {p_start} - {p_end} nm")
            self.label_step.setText(f"Step: {p_step} nm")
            self.label_geo.setText(f"Geometry: H={p_height}mm, L={p_length}mm")

            print(f"[INFO] Załadowano preset '{selected_name}' do zmiennych systemowych.")

    def toggle_fs_preset(self):
        is_checked = self.check_fs_hypercube.isChecked()
        self.label_fs_preset.setEnabled(is_checked)
        self.combo_fs_preset.setEnabled(is_checked)

    def run_focus_stacking(self):
        if not self.platform.is_ready:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona")
            return

        if self.acquisition.camera_connected and self.acquisition.camera.is_live and self.acquisition.kurios_connected:
            self.stop_live_view_action()

        image_format = self.combo_image_format.currentText()

        bottom_height = self.spin_fs_min_height.value()
        top_height = self.spin_fs_max_height.value()
        num_frames = self.spin_fs_frames.value()
        is_hypercube = self.check_fs_hypercube.isChecked()
        
        start_wavelength = self.spin_wavelength.value()
        end_wavelength = start_wavelength
        step = 10
        mode = self.combo_bandwidth.currentText()
        gain = self.spin_gain.value()

        if is_hypercube:
            selected_preset = self.combo_fs_preset.currentText()
            preset_data = self.presets.get_preset_data(selected_preset)
            if not preset_data:
                QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu!")
                return
            start_wavelength = preset_data.get("start_wavelength", 500)
            end_wavelength = preset_data.get("end_wavelength", 600)
            step = preset_data.get("step", 10)
            mode = preset_data.get("mode", "Wide")

        def __run_fs_thread():
            self.acquisition.focus_stack(
                self.platform, bottom_height, top_height, num_frames, 
                is_hypercube, start_wavelength, end_wavelength, step, mode, gain,
                self.save_path, image_format
            )

        fs_thread = threading.Thread(target=__run_fs_thread)
        fs_thread.daemon = True
        fs_thread.start()

    # zamykamy okkno jak i ODLACZAMY KAMERE I FILTR
    def on_close(self, event=None):
        print("[INFO] Zamykanie aplikacji i zwalnianie zasobów...")
        if hasattr(self, 'acquisition'):
            self.acquisition.cleanup()
        if hasattr(self, 'pwm_controller'):
            self.pwm_controller.set_pwm(0)
            self.pwm_controller.close()

        if event:
            event.accept()
        else:
            self.close()

    def closeEvent(self, event):
        self.on_close(event)
