import sys
import os
import threading
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QGroupBox, QPushButton, QLabel, QLineEdit, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QSlider, QMessageBox, QFrame, QFileDialog)
from PyQt6.QtCore import Qt
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

        # 1. Inicjalizacja potrzebnych obiektow klas, parametrow (acquisition, presets, platform bandwidth_modes)
        self.init_logic_modules()

        self.save_path = os.getcwd()

        # 2. Inicjalizacja UI 
        self.init_ui()

        # 3. Parametry wybranego presetu 
        self.preset_name = None
        self.preset_mode = None
        self.preset_start_wavelength = None
        self.preset_end_wavelength = None
        self.preset_step = None

    # --- LOGIKA I ZMIENNE ---

    # Funkcja do zainicjowania klas sterujacych sprzetem i danymi
    def init_logic_modules(self):
        self.acquisition = Acquisition()
        self.presets = PresetManager("presets.json")
        self.oculars = PresetManager("oculars.json")
        self.platform = Platform()
        self.pwm_controller = LedController(port="COM6")
        self.bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}

    # --- BUDOWANIE INTERFEJSU (GUI) ---
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)
        
        # proporcja sekcji ui (lewego panelu, srodkowego i prawego)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 4)
        main_layout.setColumnStretch(2, 1)

        # Lewy panel
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 0, 0)

        # Środkowy panel
        middle_panel = self.create_middle_panel()
        main_layout.addWidget(middle_panel, 0, 1)

        # Prawy panel
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 0, 2)

    # Lewy panel GUI: Przyciski, Statusy, Manual, Oś Z, PWM
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

    # Sekcja do wpisywania manualnych parametrow zdjecia
    def _create_manual_controls(self):
        group = QGroupBox("Parametry zdjęcia (manualne)")
        layout = QGridLayout()

        layout.addWidget(QLabel("λ [nm]"), 0, 0)
        self.spin_wavelength = QSpinBox()
        self.spin_wavelength.setRange(450, 700)
        self.spin_wavelength.setValue(500)
        self.spin_wavelength.valueChanged.connect(self.refresh_live_parameters)
        layout.addWidget(self.spin_wavelength, 0, 1)

        layout.addWidget(QLabel("Ekspozycja [µs]"), 1, 0)
        self.spin_exposure = QSpinBox()
        self.spin_exposure.setRange(100, 59269000) # range of exposure times for CS135MU camera [us]
        self.spin_exposure.setValue(50000)
        self.spin_exposure.valueChanged.connect(self.refresh_live_parameters)
        layout.addWidget(self.spin_exposure, 1, 1)

        layout.addWidget(QLabel("Gain"), 2, 0)
        self.spin_gain = QDoubleSpinBox()
        self.spin_gain.setRange(0.0, 48.0) # range of gain for CS135MU camera
        self.spin_gain.setSingleStep(0.1) 
        self.spin_gain.setValue(0.0)
        self.spin_gain.valueChanged.connect(self.refresh_live_parameters)
        layout.addWidget(self.spin_gain, 2, 1)

        self.combo_bandwidth = QComboBox()
        self.combo_bandwidth.addItems(list(self.bandwidth_modes.keys()))
        self.combo_bandwidth.currentTextChanged.connect(self.refresh_live_parameters)
        layout.addWidget(QLabel("Tryb pasma"), 3, 0)
        layout.addWidget(self.combo_bandwidth, 3, 1)

        group.setLayout(layout)
        return group

    def _create_save_path_controls(self):
        group = QGroupBox("Ścieżka zapisu")
        layout = QGridLayout()

        self.edit_save_path = QLineEdit(self.save_path)
        self.edit_save_path.setReadOnly(True)
        layout.addWidget(self.edit_save_path, 0, 0)

        btn_select_path = QPushButton("Wybierz...")
        btn_select_path.clicked.connect(self.select_save_directory)
        layout.addWidget(btn_select_path, 0, 1)

        group.setLayout(layout)
        return group

    def _create_platform_controls(self):
        group = QGroupBox("Sterowanie platformą (XYZ)")
        layout = QGridLayout()

        # Pole tekstowe na krok
        layout.addWidget(QLabel("Krok [mm]:"), 0, 0)
        self.spin_platform_step = QDoubleSpinBox()
        self.spin_platform_step.setRange(0.001, 30.0)
        self.spin_platform_step.setDecimals(3)
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

        # Przycisk wyjazdu na środek
        btn_center = QPushButton("Center")
        btn_center.clicked.connect(self.platform_move_to_center)
        layout.addWidget(btn_center, 5, 0, 1, 2)

        # Wyświetlanie aktualnej pozycji
        self.label_pos = QLabel("Pozycja: X=0.00, Y=0.00, Z=0.00")
        self.label_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_pos, 6, 0, 1, 2)

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

    # Srodkowa kolumna GUI: wyswietlanie aktywnego presetu i live view
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
        self.combo_select_preset.addItem("Wybierz preset")
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

        #Wybór okularu
        ocular_layout = QHBoxLayout()
        ocular_layout.addWidget(QLabel("Wybierz obiektyw:"))

        self.combo_select_ocular = QComboBox()
        self.combo_select_ocular.addItem("Wybierz obiektyw")
        self.combo_select_ocular.addItems(list(self.oculars.get_preset_names()))
        self.combo_select_ocular.currentTextChanged.connect(self.on_ocular_selected)
        ocular_layout.addWidget(self.combo_select_ocular)

        btn_delete_ocular = QPushButton("Usuń")
        btn_delete_ocular.clicked.connect(self.delete_ocular_action)
        ocular_layout.addWidget(btn_delete_ocular)

        layout.addLayout(ocular_layout)

        # Informacje o obiektywie
        self.label_ocular_fov = QLabel("FOV: --- x --- mm")
        layout.addWidget(self.label_ocular_fov)

        self.label_ocular_overlap = QLabel("Zakładka: --- %")
        layout.addWidget(self.label_ocular_overlap)

        group.setLayout(layout)
        return group


 
    # Prawa kolumna GUI: edytor presetów
    def create_right_panel(self):
        group = QWidget()
        main_layout = QVBoxLayout(group)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- GRUPA 1: Edytor presetów skanowania ---
        group_scan = QGroupBox("Edytor presetów skanowania")
        scan_layout = QGridLayout()

        scan_layout.addWidget(QLabel("Nazwa presetu"), 0, 0)
        self.edit_preset_name = QLineEdit("default")
        scan_layout.addWidget(self.edit_preset_name, 0, 1)

        scan_layout.addWidget(QLabel("Step [nm]"), 1, 0)
        self.combo_preset_step = QComboBox()
        self.combo_preset_step.addItems(["10", "20", "30", "40", "50"])
        self.combo_preset_step.currentTextChanged.connect(self.update_preset_constraints)
        scan_layout.addWidget(self.combo_preset_step, 1, 1)

        scan_layout.addWidget(QLabel("Mode"), 2, 0)
        self.combo_preset_mode = QComboBox()
        self.combo_preset_mode.addItems(list(self.bandwidth_modes.keys()))
        scan_layout.addWidget(self.combo_preset_mode, 2, 1)

        scan_layout.addWidget(QLabel("Start λ [nm]"), 3, 0)
        self.combo_preset_start = QComboBox()
        scan_layout.addWidget(self.combo_preset_start, 3, 1)

        scan_layout.addWidget(QLabel("Stop λ [nm]"), 4, 0)
        self.combo_preset_stop = QComboBox()
        scan_layout.addWidget(self.combo_preset_stop, 4, 1)

        scan_layout.addWidget(QLabel("Wysokość próbki [mm]"), 5, 0)
        self.spin_preset_height = QDoubleSpinBox()
        self.spin_preset_height.setRange(0.0, 200.0)
        self.spin_preset_height.setValue(10.0)
        scan_layout.addWidget(self.spin_preset_height, 5, 1)

        scan_layout.addWidget(QLabel("Długość próbki [mm]"), 6, 0)
        self.spin_preset_length = QDoubleSpinBox()
        self.spin_preset_length.setRange(0.0, 200.0)
        self.spin_preset_length.setValue(50.0)
        scan_layout.addWidget(self.spin_preset_length, 6, 1)

        btn_save = QPushButton("Zapisz preset")
        btn_save.clicked.connect(self.save_preset)
        scan_layout.addWidget(btn_save, 7, 0, 1, 2)
        group_scan.setLayout(scan_layout)
        main_layout.addWidget(group_scan)

        # --- GRUPA 2: Edytor obiektywów (Optyka) ---
        group_ocular = QGroupBox("Edytor obiektywów / optyki")
        oc_layout = QGridLayout()

        oc_layout.addWidget(QLabel("Nazwa obiektywu"), 0, 0)
        self.edit_ocular_name = QLineEdit("Plan_Apo_10x")
        oc_layout.addWidget(self.edit_ocular_name, 0, 1)

        oc_layout.addWidget(QLabel("FOV X [mm]"), 1, 0)
        self.spin_fov_x = QDoubleSpinBox()
        self.spin_fov_x.setRange(0.01, 200.0)
        self.spin_fov_x.setDecimals(3)
        self.spin_fov_x.setValue(2.500)
        self.spin_fov_x.setSingleStep(0.1)
        oc_layout.addWidget(self.spin_fov_x, 1, 1)

        oc_layout.addWidget(QLabel("FOV Y [mm]"), 2, 0)
        self.spin_fov_y = QDoubleSpinBox()
        self.spin_fov_y.setRange(0.01, 200.0)
        self.spin_fov_y.setDecimals(3)
        self.spin_fov_y.setValue(1.800)
        self.spin_fov_y.setSingleStep(0.1)
        oc_layout.addWidget(self.spin_fov_y, 2, 1)

        oc_layout.addWidget(QLabel("Zakładka (Overlap) [%]"), 3, 0)
        self.spin_overlap = QSpinBox()
        self.spin_overlap.setRange(0, 90)
        self.spin_overlap.setValue(15)
        oc_layout.addWidget(self.spin_overlap, 3, 1)

        btn_save_oc = QPushButton("Zapisz obiektyw")
        btn_save_oc.clicked.connect(self.save_ocular)
        oc_layout.addWidget(btn_save_oc, 4, 0, 1, 2)
        group_ocular.setLayout(oc_layout)
        main_layout.addWidget(group_ocular)

        main_layout.addStretch()
        self.update_preset_constraints()
        return group

    # --- OBSŁUGA ZDARZEŃ  ---

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

        wavelength = self.spin_wavelength.value()
        exposure_time = self.spin_exposure.value()
        gain = self.spin_gain.value()
        bandwidth_name = self.combo_bandwidth.currentText()
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)

        self.acquisition.capture_image(self.save_path, wavelength, exposure_time, gain, bandwidth_name, bandwidth_code)

    def refresh_live_parameters(self):
        wavelength = self.spin_wavelength.value()
        exposure = self.spin_exposure.value()
        gain = self.spin_gain.value()
        bandwidth_name = self.combo_bandwidth.currentText()

        self.acquisition.set_hardware_params(wavelength, exposure, bandwidth_name, gain)

    def start_scan(self):
        # Sprawdzanie presetu skanowania
        if not self.preset_start_wavelength:
            QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu skanowania!")
            return

        # Sprawdzanie presetu optyki
        if not hasattr(self, 'preset_fov_x') or not self.preset_fov_x:
            QMessageBox.warning(self, "Błąd", "Nie wybrano obiektywu! Wybierz go z listy po prawej stronie.")
            return

        # Pobieranie wymiarów próbki z aktualnego presetu
        preset_name = self.combo_select_preset.currentText()
        p_data = self.presets.get_preset_data(preset_name)
        sample_w = p_data.get("sample_length", 10.0)
        sample_h = p_data.get("sample_height", 10.0)

        if self.acquisition.camera_connected and self.acquisition.camera.is_live:
            print("[INFO] Zatrzymywanie Live View przed rozpoczęciem skanowania...")
            self.stop_live_view_action()

        start = self.preset_start_wavelength
        stop = self.preset_end_wavelength
        step = self.preset_step
        mode = self.preset_mode
        gain = self.spin_gain.value()

        fov_x = self.preset_fov_x
        fov_y = self.preset_fov_y
        overlap = self.preset_overlap

        print(
            f"[INFO] Uruchamianie skanowania Mozaiki: {sample_w}x{sample_h}mm (Obiektyw: {fov_x}x{fov_y}mm, Zakładka {overlap}%)")

        def run_thread():
            self.acquisition.run_mosaic_scan(
                platform=self.platform,
                save_path=self.save_path,
                starting_wavelength=start,
                ending_wavelength=stop,
                step=step,
                mode=mode,
                gain=gain,
                sample_w=sample_w,
                sample_h=sample_h,
                fov_x=fov_x,
                fov_y=fov_y,
                overlap=overlap
            )

            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self.label_pos, "setText",
                                     Qt.ConnectionType.QueuedConnection,
                                     Q_ARG(str,
                                           f"Pozycja: X={self.platform.x_state:.2f}, Y={self.platform.y_state:.2f}, Z={self.platform.z_state:.2f}"))

        scan_thread = threading.Thread(target=run_thread)
        scan_thread.daemon = True
        scan_thread.start()

    def select_save_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder do zapisu", self.save_path)
        if directory:
            self.save_path = directory
            self.edit_save_path.setText(self.save_path)
            print(f"[INFO] Ustawiono nową ścieżkę zapisu: {self.save_path}")

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

    #Platforma przemieszcza się na srodek obszaru roboczego
    def platform_move_to_center(self):
        # Sprawdzenie czy maszyna jest połączona
        if not self.platform.grbl.ser or not self.platform.grbl.ser.is_open:
            QMessageBox.warning(self, "Błąd", "Platforma nie jest połączona!\nProszę kliknąć przycisk 'Połącz'.")
            return

        # Sprawdzenie czy maszyna nie jest w stanie Alarmu
        if not self.platform.is_ready:
            QMessageBox.warning(self, "Blokada Platformy",
                                "Platforma jest zablokowana (stan Alarm).\nProszę wykonać Homing ($H) lub Unlock ($X), aby umożliwić ruch.")
            return

        self.platform.move_to_center()
        self.update_position_label()

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

    def save_ocular(self):
        name = self.edit_ocular_name.text()
        if not name:
            print("[INFO] Błąd: Podaj nazwę obiektywu!")
            return

        preset_data = {
            "fov_x_mm": self.spin_fov_x.value(),
            "fov_y_mm": self.spin_fov_y.value(),
            "overlap_percent": self.spin_overlap.value()
        }

        self.oculars.save_new_preset(name, preset_data)

        # Odświeżenie listy GUI
        updated_names = list(self.oculars.get_preset_names())
        self.combo_select_ocular.clear()
        self.combo_select_ocular.addItems(updated_names)
        self.combo_select_ocular.setCurrentText(name)

    def delete_ocular_action(self):
        selected_name = self.combo_select_ocular.currentText()
        if not selected_name:
            return

        reply = QMessageBox.question(self, "Usuwanie obiektywu",
                                     f"Czy na pewno chcesz usunąć obiektyw '{selected_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.oculars.delete_preset(selected_name)

            updated_names = list(self.oculars.get_preset_names())
            self.combo_select_ocular.blockSignals(True)
            self.combo_select_ocular.clear()
            self.combo_select_ocular.addItems(updated_names)
            self.combo_select_ocular.blockSignals(False)

            if updated_names:
                self.combo_select_ocular.setCurrentIndex(0)
                self.on_ocular_selected(self.combo_select_ocular.currentText())
            else:
                self.label_ocular_fov.setText("FOV: --- x --- mm")
                self.label_ocular_overlap.setText("Zakładka: --- %")
                self.preset_fov_x, self.preset_fov_y, self.preset_overlap = None, None, None

    def on_ocular_selected(self, text):
        selected_name = text

        # Jeśli wybrano opcję pustą lub brak tekstu
        if selected_name == "Wybierz obiektyw" or not selected_name:
            self.label_ocular_fov.setText("FOV: --- x --- mm")
            self.label_ocular_overlap.setText("Zakładka: --- %")
            self.preset_fov_x, self.preset_fov_y, self.preset_overlap = None, None, None
            return

        preset_data = self.oculars.get_preset_data(selected_name)

        if preset_data:
            self.preset_fov_x = preset_data.get("fov_x_mm", 0.0)
            self.preset_fov_y = preset_data.get("fov_y_mm", 0.0)
            self.preset_overlap = preset_data.get("overlap_percent", 0)

            self.label_ocular_fov.setText(f"FOV: {self.preset_fov_x} x {self.preset_fov_y} mm")
            self.label_ocular_overlap.setText(f"Zakładka: {self.preset_overlap} %")
            print(f"[INFO] Załadowano obiektyw '{selected_name}'.")

    def start_live_view_action(self):
        if not self.acquisition.camera_connected:
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

        # Jeśli wybrano opcję pustą lub brak tekstu
        if selected_name == "Wybierz preset" or not selected_name:
            self.label_mode.setText("Mode: ---")
            self.label_range.setText("Zakres λ: ---")
            self.label_step.setText("Step: ---")
            self.label_geo.setText("Geometry: ---")

            self.preset_mode = None
            self.preset_start_wavelength = None
            self.preset_end_wavelength = None
            self.preset_step = None
            return

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
