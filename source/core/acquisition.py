import time
import json
import os
from hardware.camera import ThorlabsCamera
from hardware.KURIOS_COMMAND_LIB import Kurios

class Acquisition:
    def __init__(self):
        self.is_scanning = False
        self.camera = None
        self.filter = None
        self.camera_connected = False
        self.kurios_connected = False

        self.manual_wavelength = 500
        self.manual_exposure = 50000
        self.manual_bandwidth = "Medium"
        self.bandwidth_modes = {"Wide": 2,
                                "Medium": 4,
                                "Narrow": 8}
        
        # Ładowanie danych konfiguracyjnych z plików JSON
        self.exposure_times = self._load_json("source/data/exposure_time.json")
        self.tuning_times = self._load_json("source/data/tuning_times.json")

    def _load_json(self, path):
        if not os.path.exists(path):
            # Wypisujemy tylko info, nie przerywamy działania (użyte zostaną wartości domyślne)
            print(f"[INFO] Plik konfiguracyjny {path} nie został znaleziony.")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[INFO] Błąd podczas ładowania {path}: {e}")
            return {}

    def connect_hardware(self):
        print("[INFO] Connecting hardware...")

        if self.is_scanning:
            print("[INFO] Nie można łączyć urządzeń podczas skanowania!")
            return False

        try:
            # 1. Łączenie z Kamerą
            self.camera = ThorlabsCamera(self.manual_exposure)
            self.camera_connected = True
            print("[CAM] Kamera połączona.")

            # 2. Łączenie z Filtrem KURIOS
            self.filter = Kurios()

            # Musimy znaleźć urządzenia podłączone do komputera
            devices = self.filter.list_devices()
            if not devices:
                print("[CAM] Błąd: Nie znaleziono urządzenia KURIOS na USB.")
                self.kurios_connected = False
                return False

            # bierzemy pierwsze znalezione urządzenie
            serial_port = devices[0][0]

            # otwieramy połączenie
            status = self.filter.open(serial_port, 115200, 1)

            if status >= 0:
                self.kurios_connected = True
                print(f"[CAM] KURIOS połączony na porcie: {serial_port}")
            else:
                print("[CAM] Błąd: Nie udało się otworzyć portu KURIOS.")
                self.kurios_connected = False
                return False

        except Exception as e:
            print(f"[CAM] Krytyczny błąd połączenia: {e}")
            return False

        return True

    def capture_image(self, wavelength, exposure, gain, bandwidth_name, bandwidth_code):
        if not self.camera or not self.filter:
            print("[INFO] Najpierw połącz urządzenia!")
            return

        if self.is_scanning:
            print("[INFO] Trwa skanowanie")
            return

        # Ustawienie parametrow filtra:
        # - długość fali w zakresie [430; 700] nm,
        # - tryb przepustowosci: 1 = BLACK mode, 2 = WIDE, 4 = MEDIUM mode, 8 = NARROW mode
        self.filter.SetWavelength(wavelength)
        self.filter.SetBandwidthMode(bandwidth_code)

        # kamera
        self.camera.exposure_time_us = exposure
        try:
            if hasattr(self.camera, "gain"):
                    self.camera.gain = gain
            elif hasattr(self.camera, "analog_gain"):
                    self.camera.analog_gain = gain
        except Exception as e:
            print(f"[CAM] Gain nie mógł zostać ustawiony: {e}")

        time.sleep(0.3)

        filename = f"manual_{wavelength}nm_{bandwidth_name}.png"
        self.camera.save_frame(filename)
        print(f"[CAM] Zapisano zdjęcie: {filename}")

    def set_hardware_params(self, wavelength, exposure, bandwidth_name, gain):
        """Aktualizuje parametry sprzetu (Live View) bez zapisu zdjecia."""
        if self.filter and self.kurios_connected:
            bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)
            self.filter.SetWavelength(wavelength)
            self.filter.SetBandwidthMode(bandwidth_code)

        if self.camera and self.camera_connected:
            # Ustawiamy ekspozycje kamery
            self.camera.exposure_time_us = exposure
            # W SDK zmiana exposure_time_us zwykle aplikuje sie natychmiastowo
            try:
                if hasattr(self.camera, "gain"):
                    self.camera.gain = gain
                elif hasattr(self.camera, "analog_gain"):
                    self.camera.analog_gain = gain
            except Exception:
                pass
            # dla kolejnych klatek

    def start_live_view(self):
        if self.camera and self.camera_connected:
            return self.camera.start_live_view()

    def stop_live_view(self):
        if self.camera and self.camera_connected:
            self.camera.stop_live_view()

    def scan_sequence(self, starting_wavelength, ending_wavelength, step, mode, gain):

        if not self.camera or not self.filter:
            print("[INFO] Najpierw połącz urządzenia!")
            return

        if self.is_scanning:
            print("[INFO] Skanowanie już trwa!")
            return

        self.is_scanning = True

        # ustawiamy tryb filtra na manualny
        self.filter.SetOutputMode(1)

        wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))

        bandwidth_name = mode
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4) # jak sie wykrzaczy to domyslnie na 4 ustawiony tryb

        self.filter.SetBandwidthMode(bandwidth_code)
        time.sleep(0.2)

        # Ustawiamy Gain przed rozpoczęciem pętli
        try:
            if hasattr(self.camera, "gain"):
                self.camera.gain = gain
            elif hasattr(self.camera, "analog_gain"):
                self.camera.analog_gain = gain
        except Exception as e:
            print(f"[CAM] Gain nie mógł zostać ustawiony dla skanowania: {e}")

        print(f"[INFO] Rozpoczynam skanowanie: {starting_wavelength}–{ending_wavelength} nm, step={step}, mode={bandwidth_name}")

        prev_wavelength = wavelengths[0]

        for i, wavelength in enumerate(wavelengths):
            self.filter.SetWavelength(wavelength)

            if i > 0:
                # Pobieramy czas przestrojenia z JSON (klucz w formacie "start,end")
                key = f"{prev_wavelength},{wavelength}"
                delay_ms = self.tuning_times.get(bandwidth_name, {}).get(key, 200)
                time.sleep(delay_ms / 1000.0)
            else:
                time.sleep(0.2)

            # Pobieramy czas ekspozycji z JSON (klucz to string)
            exp = self.exposure_times.get(bandwidth_name, {}).get(str(wavelength), 10000)
            self.camera.exposure_time_us = exp

            filename = f"scan_{i+1}_{wavelength}nm_{bandwidth_name}.png"
            self.camera.save_frame(filename)

            print(f"[CAM] Zapisano {filename} (ekspozycja: {exp} µs)")
            prev_wavelength = wavelength

        # Czas powrotu do 450 nm (z 700 nm)
        delay_back = self.tuning_times.get(bandwidth_name, {}).get("700,450", 200)
        self.filter.SetWavelength(450)
        time.sleep(delay_back / 1000.0)

        self.is_scanning = False
        print("[INFO] Skanowanie zakończone.")

    def cleanup(self):
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()