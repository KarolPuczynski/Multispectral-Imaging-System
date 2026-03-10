import sys
import threading
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QGroupBox, QPushButton, QLabel, QLineEdit, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QSlider, QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from core.acquisition import Acquisition
from core.preset_handling import PresetManager
from core.move_platform import Platform
from gui.live_view import LiveViewWidget

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multispectral System")

        # 1. Inicjalizacja potrzebnych obiektow klas, parametrow (acquisition, presets, platform bandwidth_modes)
        self.init_logic_modules()

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
        self.platform = Platform()
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

        # Manualne sterowanie
        layout.addWidget(self._create_manual_controls())

        # Oś XYZ i PWM
        layout.addWidget(self._create_platform_controls())
        layout.addWidget(self._create_pwm_controls())

        layout.addStretch() # Wypchnięcie elementów do góry
        group_box.setLayout(layout)
        return group_box

    # Sekcja do wpisywania manualnych parametrow zdjecia
    def _create_manual_controls(self):
        group = QGroupBox("Parametry zdjęcia (manualne)")
        layout = QGridLayout()

        layout.addWidget(QLabel("λ [nm]"), 0, 0)
        self.spin_wavelength = QSpinBox()
        self.spin_wavelength.setRange(400, 900)
        self.spin_wavelength.setValue(500)
        layout.addWidget(self.spin_wavelength, 0, 1)

        layout.addWidget(QLabel("Ekspozycja [µs]"), 1, 0)
        self.spin_exposure = QSpinBox()
        self.spin_exposure.setRange(100, 1000000)
        self.spin_exposure.setValue(50000)
        layout.addWidget(self.spin_exposure, 1, 1)

        layout.addWidget(QLabel("Tryb pasma"), 2, 0)
        self.combo_bandwidth = QComboBox()
        self.combo_bandwidth.addItems(list(self.bandwidth_modes.keys()))
        self.combo_bandwidth.setCurrentText("Medium")
        layout.addWidget(self.combo_bandwidth, 2, 1)

        group.setLayout(layout)
        return group

    def _create_platform_controls(self):
        group = QGroupBox("Sterowanie platformą (XYZ)")
        layout = QGridLayout()

        # Pole tekstowe na krok
        layout.addWidget(QLabel("Krok [mm]:"), 0, 0)
        self.spin_platform_step = QDoubleSpinBox()
        self.spin_platform_step.setRange(0.01, 50.0)
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

        self.btn_live = QPushButton("Start Live View")
        self.btn_live.clicked.connect(self.toggle_live_view)
        layout.addWidget(self.btn_live)

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

    # Prawa kolumna GUI: edytor presetów
    def create_right_panel(self):
        group = QGroupBox("Edytor presetów")
        layout = QGridLayout()

        layout.addWidget(QLabel("Nazwa presetu"), 0, 0)
        self.edit_preset_name = QLineEdit("default")
        layout.addWidget(self.edit_preset_name, 0, 1)

        layout.addWidget(QLabel("Mode"), 1, 0)
        self.combo_preset_mode = QComboBox()
        self.combo_preset_mode.addItems(list(self.bandwidth_modes.keys()))
        layout.addWidget(self.combo_preset_mode, 1, 1)

        layout.addWidget(QLabel("Start λ [nm]"), 2, 0)
        self.spin_preset_start = QSpinBox()
        self.spin_preset_start.setRange(400, 900)
        self.spin_preset_start.setValue(500)
        layout.addWidget(self.spin_preset_start, 2, 1)

        layout.addWidget(QLabel("Stop λ [nm]"), 3, 0)
        self.spin_preset_stop = QSpinBox()
        self.spin_preset_stop.setRange(400, 900)
        self.spin_preset_stop.setValue(600)
        layout.addWidget(self.spin_preset_stop, 3, 1)

        layout.addWidget(QLabel("Step [nm]"), 4, 0)
        self.spin_preset_step = QSpinBox()
        self.spin_preset_step.setRange(1, 100)
        self.spin_preset_step.setValue(10)
        layout.addWidget(self.spin_preset_step, 4, 1)

        btn_save = QPushButton("Zapisz preset")
        btn_save.clicked.connect(self.save_preset)
        layout.addWidget(btn_save, 5, 0, 1, 2) # span 2 columns

        layout.setRowStretch(6, 1) # push up
        group.setLayout(layout)
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
        else:
            pass

    # przechwytywanie zdjecia z manulnymi parametrami
    def capture_image(self):
        wavelength = self.spin_wavelength.value()
        exposure_time = self.spin_exposure.value()
        bandwidth_name = self.combo_bandwidth.currentText()
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)

        self.acquisition.capture_image(wavelength, exposure_time, 1.0, bandwidth_name, bandwidth_code)

    # skanowanie zakresu z paramsami z presetow
    def start_scan(self):
        if not self.preset_start_wavelength:
            QMessageBox.warning(self, "Błąd", "Nie wybrano poprawnego presetu!")
            return
            
        start = self.preset_start_wavelength
        stop = self.preset_end_wavelength
        step = self.preset_step
        mode = self.preset_mode

        print(f"Próba uruchomienia skanowania: {start}-{stop}nm, step {step}, mode {mode}")

        def run_thread():
            self.acquisition.scan_sequence(start, stop, step, mode)
            print("Wątek skanowania zakończony.")

        scan_thread = threading.Thread(target=run_thread)
        scan_thread.daemon = True
        scan_thread.start()

    # sprawdzamy czy uzytkownik nie wpisal za duzej wartosci kroku 
    # trzeba i tak jakos zabezpieczyc przed wyslaniem wartosci jak 
    # bedziemy bardzo blisko krawedzi zakresu
    def validate_and_move(self, axis, direction):
        step = self.spin_platform_step.value()

        # 2. Sprawdzenie czy wartość jest dodatnia
        if step <= 0:
            QMessageBox.warning(self, "Ostrzeżenie", "Krok musi być wartością dodatnią.")
            return

        # 3. Zabezpieczenie przed zbyt dużym krokiem (np. max 30mm)
        if step > 30.0:
            QMessageBox.warning(self, "Ostrzeżenie", f"Wartość {step} mm jest zbyt duża! Maksymalny bezpieczny krok to 50 mm.")
            return

        dist = step * direction # np. 5.0 * -1 = -5.0
        if axis == 'Z': 
            dist = dist / 5 # wspolczynnik skalowanosci os Z (XD)
        self.move_single_axis(f'G91')
        self.move_single_axis(f'G1 {axis}{dist} F500')

    # reczny ruch na osi
    def move_single_axis(self, gcode = 'G91 X1'):
        self.platform.move_single_axis(gcode)

    # homing platformy 
    def platform_homing(self):
        self.platform.homing()

    # Odblokowanie platformy (domyslnie po wlaczeniu jest zablokowana, i wtedy można tylko ja homingowac)
    def platform_unlock(self):
        self.platform.unlock()

    # regulacja oswietleenia probki
    def adjust_lighting(self):
        val = self.pwm_slider.value()
        self.label_pwm_val.setText(f"PWM: {val}")
        # self.platform.adjust_lighting(val) # zakładając, że metoda przyjmuje parametr
        pass

    def save_preset(self):
        name = self.edit_preset_name.text()
        if not name:
            print("Błąd: Podaj nazwę presetu!")
            return

        preset_data = {
            "mode": self.combo_preset_mode.currentText(),
            "start_wavelength": self.spin_preset_start.value(),
            "end_wavelength": self.spin_preset_stop.value(),
            "step": self.spin_preset_step.value()
        }

        self.presets.save_new_preset(name, preset_data)

        updated_names = list(self.presets.get_preset_names())
        self.combo_select_preset.clear()
        self.combo_select_preset.addItems(updated_names)

    def toggle_live_view(self):
        # Sprawdzamy czy hardware jest podłączony
        if not self.acquisition.camera_connected:
            print("Najpierw połącz kamerę!")
            return

        if self.btn_live.text() == "Start Live View":
            # Start
            queue = self.acquisition.camera.start_live_view()
            if queue:
                self.live_view_widget.start_live_view(queue)
                self.btn_live.setText("Stop Live View")
        else:
            # Stop
            self.live_view_widget.stop_live_view()
            self.acquisition.camera.stop_live_view()
            self.btn_live.setText("Start Live View")

    def on_preset_selected(self, text):
        selected_name = text

        preset_data = self.presets.get_preset_data(selected_name)

        if preset_data:
            p_mode = preset_data.get("mode", "Wide")
            p_start = preset_data.get("start_wavelength", 500)
            p_end = preset_data.get("end_wavelength", 600)
            p_step = preset_data.get("step", 10)

            self.preset_mode = p_mode
            self.preset_start_wavelength = p_start
            self.preset_end_wavelength = p_end
            self.preset_step = p_step

            self.label_mode.setText(f"Mode: {p_mode}")
            self.label_range.setText(f"Zakres λ: {p_start} - {p_end} nm")
            self.label_step.setText(f"Step: {p_step} nm")

            print(f"Załadowano preset '{selected_name}' do zmiennych systemowych.")

    # zamykamy okkno jak i ODLACZAMY KAMERE I FILTR
    def on_close(self, event=None):
        print("Zamykanie aplikacji i zwalnianie zasobów...")
        if hasattr(self, 'acquisition'):
            self.acquisition.cleanup()

        if event:
            event.accept()
        else:
            self.close()

    def closeEvent(self, event):
        self.on_close(event)
