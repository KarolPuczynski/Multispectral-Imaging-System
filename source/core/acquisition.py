import time
from config.settings import kurios_tuning_times, exposure_times
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

    def connect_hardware(self):
        print("[INFO] Connecting hardware...")

        if self.is_scanning:
            print("Nie można łączyć urządzeń podczas skanowania!")
            return False

        try:
            # 1. Łączenie z Kamerą
            self.camera = ThorlabsCamera(self.manual_exposure)
            self.camera_connected = True
            print("Kamera połączona.")

            # 2. Łączenie z Filtrem KURIOS
            self.filter = Kurios()

            # Musimy znaleźć urządzenia podłączone do komputera
            devices = self.filter.list_devices()
            if not devices:
                print("Błąd: Nie znaleziono urządzenia KURIOS na USB.")
                self.kurios_connected = False
                return False

            # bierzemy pierwsze znalezione urządzenie
            serial_port = devices[0][0]

            # otwieramy połączenie
            status = self.filter.open(serial_port, 115200, 1)

            if status >= 0:
                self.kurios_connected = True
                print(f"KURIOS połączony na porcie: {serial_port}")
            else:
                print("Błąd: Nie udało się otworzyć portu KURIOS.")
                self.kurios_connected = False
                return False

        except Exception as e:
            print(f"Krytyczny błąd połączenia: {e}")
            return False

        return True

    def capture_image(self, wavelength, exposure, gain, bandwidth_name, bandwidth_code):
        if not self.camera or not self.filter:
            print("Najpierw połącz urządzenia!")
            return

        if self.is_scanning:
            print("Trwa skanowanie")
            return

        # Ustawienie parametrow filtra:
        # - długość fali w zakresie [430; 700] nm,
        # - tryb przepustowosci: 1 = BLACK mode, 2 = WIDE, 4 = MEDIUM mode, 8 = NARROW mode
        self.filter.SetWavelength(wavelength)
        self.filter.SetBandwidthMode(bandwidth_code)

        # kamera
        self.camera.exposure_time_us = exposure
        try:
            self.camera.analog_gain = gain
        except Exception as e:
            print("Gain nie mógł zostać ustawiony:", e)

        time.sleep(0.3)

        filename = f"manual_{wavelength}nm_{bandwidth_name}.png"
        self.camera.save_frame(filename)
        print(f"Zapisano zdjęcie: {filename}")

    def scan_sequence(self, starting_wavelength, ending_wavelength, step, mode):

        if not self.camera or not self.filter:
            print("Najpierw połącz urządzenia!")
            return

        if self.is_scanning:
            print("Skanowanie już trwa!")
            return

        self.is_scanning = True

        # ustawiamy tryb filtra na manualny
        self.filter.SetOutputMode(1)

        wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))

        bandwidth_name = mode
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4) # jak sie wykrzaczy to domyslnie na 4 ustawiony tryb

        self.filter.SetBandwidthMode(bandwidth_code)
        time.sleep(0.2)

        print(f"Rozpoczynam skanowanie: {starting_wavelength}–{ending_wavelength} nm, step={step}, mode={bandwidth_name}")

        prev_wavelength = wavelengths[0]

        for i, wavelength in enumerate(wavelengths):
            self.filter.SetWavelength(wavelength)

            if i > 0:
                delay_ms = kurios_tuning_times[bandwidth_name].get((prev_wavelength, wavelength), 200)
                time.sleep(delay_ms / 1000.0)
            else:
                time.sleep(0.2)

            exp = exposure_times[bandwidth_name].get(wavelength, 10000)
            self.camera.exposure_time_us = exp

            filename = f"scan_{i+1}_{wavelength}nm_{bandwidth_name}.png"
            self.camera.save_frame(filename)

            print(f"Zapisano {filename} (ekspozycja: {exp} µs)")
            prev_wavelength = wavelength

        delay_back = kurios_tuning_times[bandwidth_name].get((700, 450), 200)
        self.filter.SetWavelength(450)
        time.sleep(delay_back / 1000.0)

        self.is_scanning = False
        print("Skanowanie zakończone.")

    def cleanup(self):
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()