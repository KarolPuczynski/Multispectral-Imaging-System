import tkinter as tk
from tkinter import ttk
import threading

from core.acquisition import Acquisition
from core.preset_handling import PresetManager
from core.move_platform import Platform

from gui.live_view import LiveViewCanvas

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Multispectral System")

        # 1. Inicjalizacja potrzebnych obiektow klas, parametrow (acquisition, presets, platform bandwidth_modes)
        self.init_logic_modules()

        # 2. Zmienne (StringVars, IntVars etc.)
        self.init_variables()

        # 3. Ustawienia siatki okna
        self.setup_window_grid()

        # 4. Budowanie paneli
        self.create_left_panel()  # Urządzenia, Manual, Oś Z, PWM
        self.create_middle_panel()  # Wyświetlanie presetu
        self.create_right_panel()  # Edytor presetow

        # 5. Zamykanie
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- LOGIKA I ZMIENNE ---

    # Funkcja do zainicjowania klas sterujacych sprzetem i danymi
    def init_logic_modules(self):
        self.acquisition = Acquisition()
        self.presets = PresetManager("presets.json")
        self.platform = Platform()
        self.bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}

    # Zainicjowanie wszystkich zmiennych Tkinter używanych w GUI
    def init_variables(self):
        # Statusy
        self.cam_status = tk.StringVar(value="Kamera: Rozłączona")
        self.kur_status = tk.StringVar(value="KURIOS: Rozłączony")

        # Manualne parametry
        self.var_wavelength = tk.IntVar(value=500)
        self.var_exposure = tk.IntVar(value=2000)
        self.var_bandwidth = tk.StringVar(value="Medium")

        # Parametry wybranego presetu
        self.var_selected_combo_item = tk.StringVar(value="default")
        self.preset_name = None
        self.preset_mode = None
        self.preset_start_wavelength = None
        self.preset_end_wavelength = None
        self.preset_step = None

        # Presety
        self.var_preset_name = tk.StringVar(value="default")
        self.var_preset_mode = tk.StringVar(value="Wide")
        self.var_preset_start_wavelength = tk.IntVar(value=500)
        self.var_preset_end_wavelength = tk.IntVar(value=600)
        self.var_preset_step = tk.IntVar(value=10)

        # PWM
        self.pwm_value = tk.IntVar(value=128)

    # Konfiguracja siatki głównego okna
    def setup_window_grid(self):
        for col in range(3):
            self.root.columnconfigure(col, weight=1)
        self.root.rowconfigure(0, weight=1)

    # --- BUDOWANIE INTERFEJSU (GUI) ---

    # Lewy panel GUI: Przyciski, Statusy, Manual, Oś Z, PWM
    def create_left_panel(self):
        left_frame = ttk.LabelFrame(self.root, text="Urządzenia & akwizycja")
        left_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Przyciski sterujące
        buttons = {
            "Połącz": self.connect,
            "Zrób zdjęcie": self.capture_image,
            "Skanuj zakres": self.start_scan,
            "Zakończ": self.on_close
        }

        row_idx = 0
        for text, command in buttons.items():
            ttk.Button(left_frame, text=text, command=command).grid(row=row_idx, column=0, columnspan=2, sticky="ew")
            row_idx += 1

        # Statusy polaczania kamery i filtra
        self.cam_status_label = tk.Label(left_frame, textvariable=self.cam_status, fg="red")
        self.cam_status_label.grid(row=row_idx, column=0, columnspan=2, sticky="w")
        row_idx += 1

        self.kur_status_label = tk.Label(left_frame, textvariable=self.kur_status, fg="red")
        self.kur_status_label.grid(row=row_idx, column=0, columnspan=2, sticky="w")
        row_idx += 1

        # Manualne sterowanie
        self._create_manual_controls(left_frame, start_row=row_idx)

        # Oś Z i PWM
        self._create_z_axis_controls(left_frame, start_row=row_idx + 4)
        self._create_pwm_controls(left_frame, start_row=row_idx + 5)

    # Sekcja do wpisywania manualnych parametrow zdjecia
    def _create_manual_controls(self, parent, start_row):
        manual_frame = ttk.LabelFrame(parent, text="Parametry zdjęcia (manualne)")
        manual_frame.grid(row=start_row, column=0, columnspan=2, pady=5, sticky="ew")

        ttk.Label(manual_frame, text="λ [nm]").grid(row=0, column=0, sticky="w")
        ttk.Entry(manual_frame, textvariable=self.var_wavelength, width=10).grid(row=0, column=1)

        ttk.Label(manual_frame, text="Ekspozycja [µs]").grid(row=1, column=0, sticky="w")
        ttk.Entry(manual_frame, textvariable=self.var_exposure, width=10).grid(row=1, column=1)

        ttk.Label(manual_frame, text="Tryb pasma").grid(row=3, column=0, sticky="w")
        ttk.Combobox(
            manual_frame,
            textvariable=self.var_bandwidth,
            values=list(self.bandwidth_modes.keys()),
            state="readonly",
            width=10
        ).grid(row=3, column=1)

    def _create_z_axis_controls(self, parent, start_row):
        z_frame = ttk.LabelFrame(parent, text="Oś Z ")
        z_frame.grid(row=start_row, column=0, columnspan=2, pady=5, sticky="ew")
        ttk.Button(z_frame, text="Z +", command=self.move_single_axis).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(z_frame, text="Z -", command=self.move_single_axis).grid(row=0, column=1, sticky="ew", padx=2, pady=2)

    def _create_pwm_controls(self, parent, start_row):
        pwm_frame = ttk.LabelFrame(parent, text="Oświetlenie (PWM)")
        pwm_frame.grid(row=start_row, column=0, columnspan=2, pady=5, sticky="ew")

        ttk.Scale(
            pwm_frame, from_=0, to=255, variable=self.pwm_value,
            orient="horizontal", command=self.adjust_lighting
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=5)

        ttk.Label(pwm_frame, text="PWM: 128").grid(row=1, column=0, columnspan=2)


    # Srodkowa kolumna GUI: wyswietlanie aktywnego presetu i live view
    def create_middle_panel(self):
        mid_frame = ttk.LabelFrame(self.root, text="Podgląd i Preset")
        mid_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        # LIVE VIEW
        # Kontener na obraz z kamery
        self.live_view_frame = tk.Frame(mid_frame, width=400, height=300, bg="black")
        self.live_view_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.live_view_frame.grid_propagate(False)

        self.live_canvas = LiveViewCanvas(self.live_view_frame)

        self.btn_live = ttk.Button(mid_frame, text="Start Live View", command=self.toggle_live_view)
        self.btn_live.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        # PRESETY
        ttk.Separator(mid_frame, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(mid_frame, text="Wybierz preset:").grid(row=3, column=0, sticky="w")
        self.preset_combo = ttk.Combobox(
            mid_frame,
            textvariable=self.var_selected_combo_item,
            values=list(self.presets.get_preset_names()),
            state="readonly",
            width=20
        )
        self.preset_combo.grid(row=3, column=1, sticky="ew")
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)

        self.label_mode = ttk.Label(mid_frame, text="Mode: ---")
        self.label_mode.grid(row=4, column=0, columnspan=2, sticky="w")

        self.label_range = ttk.Label(mid_frame, text="Zakres λ: ---")
        self.label_range.grid(row=5, column=0, columnspan=2, sticky="w")

        self.label_step = ttk.Label(mid_frame, text="Step: ---")
        self.label_step.grid(row=6, column=0, columnspan=2, sticky="w")

        self.label_geo = ttk.Label(mid_frame, text="Geometry: ---")
        self.label_geo.grid(row=7, column=0, columnspan=2, sticky="w")


    # Prawa kolumna GUI: edytor presetów
    def create_right_panel(self):
        preset_frame = ttk.LabelFrame(self.root, text="Edytor presetów")
        preset_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        fields = [
            ("Nazwa presetu", self.var_preset_name),
            ("Mode", self.var_preset_mode),
            ("Start λ [nm]", self.var_preset_start_wavelength),
            ("Stop λ [nm]", self.var_preset_end_wavelength),
            ("Step [nm]", self.var_preset_step)
        ]

        for i, (label_text, variable) in enumerate(fields):
            ttk.Label(preset_frame, text=label_text).grid(row=i, column=0, sticky="w")
            if i != 1:
                ttk.Entry(preset_frame, textvariable=variable, width=20).grid(row=i, column=1)
            else:
                ttk.Combobox(
                    preset_frame,
                    textvariable=self.var_preset_mode,
                    values=list(self.bandwidth_modes.keys()),
                    state="readonly",
                    width=10
                ).grid(row=i, column=1)

        ttk.Button(
            preset_frame, text="Zapisz preset", command=self.save_preset
        ).grid(row=len(fields) + 1, column=0, columnspan=2, pady=15, sticky="ew")

    # --- OBSŁUGA ZDARZEŃ  ---

    # Łączenie się z kamera i filtrem przestrajalnym
    def connect(self):
        success = self.acquisition.connect_hardware()

        if success:
            self.cam_status.set("Kamera: POŁĄCZONA")
            self.cam_status_label.configure(fg="green")

            self.kur_status.set("KURIOS: POŁĄCZONY")
            self.kur_status_label.configure(fg="green")
        else:
            pass

    # Przechwytywanie zdjęcia zgodnie z manualnymi wartosciami wpisanymi przez uzytkownika
    def capture_image(self):
        wavelength = self.var_wavelength.get()
        exposure_time = self.var_exposure.get()
        bandwidth_name = self.var_bandwidth.get()
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)

        self.acquisition.capture_image(wavelength, exposure_time, 1.0, bandwidth_name, bandwidth_code)

    # Skanowanie (robienie wielu zdjec dla okresllonych parametrow) probki zgodnie z wartosciami w wybranym presecie
    def start_scan(self):
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

    # Reczny ruch na wybranej osi
    def move_single_axis(self, gcode = 'G91 X10'):
        self.platform.move_single_axis(gcode)

    # Dostosowanie mocy naświetlania probki
    def adjust_lighting(self):
        self.platform.adjust_lighting()

    # Zapisanie presetu do pliku presets.json
    def save_preset(self):
        # Nazwa presetu i sprawdzenie czy jakakolwiek jest
        name = self.var_preset_name.get()
        if not name:
            print("Błąd: Podaj nazwę presetu!")
            return

        # pobranie danych z entry boxow z gui do presetu
        preset_data = {
            "mode": self.var_preset_mode.get(),
            "start_wavelength": self.var_preset_start_wavelength.get(),
            "end_wavelength": self.var_preset_end_wavelength.get(),
            "step": self.var_preset_step.get()
        }

        # wywolanie funkcji save_new_preset z core.preset_handling
        self.presets.save_new_preset(name, preset_data)

        # Odswiezenie listy dla aktywnego presetu (srodkowy panel)
        updated_names = list(self.presets.get_preset_names())
        self.preset_combo["values"] = updated_names

    def toggle_live_view(self):
        # Sprawdzamy czy hardware jest podłączony
        if not self.acquisition.camera_connected:
            print("Najpierw połącz kamerę!")
            return

        if self.btn_live["text"] == "Start Live View":
            # Start
            queue = self.acquisition.camera.start_live_view()
            if queue:
                self.live_canvas.start(queue)
                self.btn_live["text"] = "Stop Live View"
        else:
            # Stop
            self.live_canvas.stop()
            self.acquisition.camera.stop_live_view()
            self.btn_live["text"] = "Start Live View"

    # Wyswietlenie paramatrow wybranego presetu, ktory bedzie uzywany do skanowania
    def on_preset_selected(self, event):
        selected_name = self.preset_combo.get()

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

            self.label_mode.config(text=f"Mode: {p_mode}")
            self.label_range.config(text=f"Zakres λ: {p_start} - {p_end} nm")
            self.label_step.config(text=f"Step: {p_step} nm")

            print(f"Załadowano preset '{selected_name}' do zmiennych systemowych.")

    # Obsluga wylaczenia programu jak i zapewnienie o poprawnym rozlaczeniu sie z hardware'em
    def on_close(self):
        print("Zamykanie aplikacji i zwalnianie zasobów...")
        if hasattr(self, 'acquisition'):
            self.acquisition.cleanup()

        self.root.destroy()

