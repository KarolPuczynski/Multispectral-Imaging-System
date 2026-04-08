import time
import json
import os
import math
from hardware.camera import ThorlabsCamera
from PIL import Image
from hardware.KURIOS_COMMAND_LIB import Kurios
from core.stitching import MosaicStitcher

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
        self.exposure_times = self._load_json("source/data/exposure_times.json")
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

    def capture_image(self, save_path, wavelength, exposure, gain, bandwidth_name, bandwidth_code):
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
        self.camera.camera.exposure_time_us = exposure
        try:
            if hasattr(self.camera.camera, "gain"):
                    self.camera.camera.gain = gain
            elif hasattr(self.camera.camera, "analog_gain"):
                    self.camera.camera.analog_gain = gain
        except Exception as e:
            print(f"[CAM] Gain nie mógł zostać ustawiony: {e}")

        time.sleep(0.3)

        filename = f"manual_{wavelength}nm_{bandwidth_name}.tiff"
        full_path = os.path.join(save_path, filename)
        self.camera.save_frame(full_path)
        print(f"[CAM] Zapisano zdjęcie: {full_path}")

    def set_hardware_params(self, wavelength, exposure, bandwidth_name, gain):
        """Aktualizuje parametry sprzetu (Live View) bez zapisu zdjecia."""
        if self.filter and self.kurios_connected:
            bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)
            self.filter.SetWavelength(wavelength)
            self.filter.SetBandwidthMode(bandwidth_code)

        if self.camera and self.camera_connected:
            self.camera.camera.exposure_time_us = exposure
            try:
                if hasattr(self.camera.camera, "gain"):
                    self.camera.camera.gain = gain
                elif hasattr(self.camera.camera, "analog_gain"):
                    self.camera.camera.analog_gain = gain
            except Exception:
                pass

    def start_live_view(self):
        if self.camera and self.camera_connected:
            return self.camera.start_live_view()

    def stop_live_view(self):
        if self.camera and self.camera_connected:
            self.camera.stop_live_view()

    def generate_scan_grid(self, sample_width, sample_height, fov_x, fov_y, overlap_percent):

        if fov_x <= 0 or fov_y <= 0 or sample_width <= 0 or sample_height <= 0:
            print("[INFO] Błędne wymiary FOV lub próbki. Zwracam pustą siatkę.")
            return []

        overlap_factor = overlap_percent / 100.0
        step_x = fov_x * (1.0 - overlap_factor)
        step_y = fov_y * (1.0 - overlap_factor)

        cols = max(1, math.ceil(sample_width / step_x))
        rows = max(1, math.ceil(sample_height / step_y))

        # Obliczamy o ile musimy przesunąć siatkę, żeby (0,0) było dokładnie w jej centrum
        offset_x = ((cols - 1) * step_x) / 2.0
        offset_y = ((rows - 1) * step_y) / 2.0

        grid_points = []

        for r in range(rows):
            # Odejmujemy offset, więc zaczynamy od wartości ujemnych
            y = (r * step_y) - offset_y

            col_range = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)

            for c in col_range:
                x = (c * step_x) - offset_x
                grid_points.append((x, y))

        print(
            f"[INFO] Wygenerowano wyśrodkowaną siatkę: {cols}x{rows} ({len(grid_points)} pkt). Offset do rogu: X={-offset_x:.2f}, Y={-offset_y:.2f}")
        return grid_points

    def scan_sequence(self, platform, save_path, starting_wavelength, ending_wavelength, step, mode, gain,
                             sample_w, sample_h, fov_x, fov_y, overlap):
        if not self.camera or not self.filter:
            print("[INFO] Najpierw połącz urządzenia optyczne!")
            return
        if not platform.grbl.ser or not platform.grbl.ser.is_open:
            print("[INFO] Najpierw połącz platformę!")
            return
        if self.is_scanning:
            print("[INFO] Skanowanie już trwa!")
            return

        self.is_scanning = True
        self.filter.SetOutputMode(1)

        # Generowanie siatki
        grid_points = self.generate_scan_grid(sample_w, sample_h, fov_x, fov_y, overlap)
        if not grid_points:
            self.is_scanning = False
            return

        # Zapisujemy pozycję startową jako pozycję (0,0)
        center_x = platform.x_state
        center_y = platform.y_state
        print(f"[INFO] Rozpoczynam skanowanie. Środek próbki: X={center_x:.2f}, Y={center_y:.2f}")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mosaic_dir = os.path.join(save_path, f"Mosaic_{timestamp}")
        os.makedirs(mosaic_dir, exist_ok=True)

        bandwidth_name = mode
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)
        self.filter.SetBandwidthMode(bandwidth_code)
        time.sleep(0.2)

        try:
            if hasattr(self.camera.camera, "gain"):
                self.camera.camera.gain = gain
            elif hasattr(self.camera.camera, "analog_gain"):
                self.camera.camera.analog_gain = gain
        except Exception:
            pass

        wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))
        metadata_tiles = []

        # Główna pętla po kafelkach
        for tile_idx, (dx, dy) in enumerate(grid_points):
            target_x = center_x + dx
            target_y = center_y + dy

            print(
                f"\n[SCAN] --- Kafelek {tile_idx + 1}/{len(grid_points)} --- (Ruch do X={target_x:.2f}, Y={target_y:.2f})")

            # Ruch fizyczny platformy
            platform.move_to_position_blocking(target_x, target_y)

            captured_data = []
            prev_wavelength = wavelengths[0]

            # Pętla spektralna
            for i, wavelength in enumerate(wavelengths):
                self.filter.SetWavelength(wavelength)
                if i > 0:
                    key = f"{prev_wavelength},{wavelength}"
                    delay_ms = self.tuning_times.get(bandwidth_name, {}).get(key, 200)
                    time.sleep(delay_ms / 1000.0)
                else:
                    time.sleep(0.2)

                exp = self.exposure_times.get(bandwidth_name, {}).get(str(wavelength), 10000)
                self.camera.camera.exposure_time_us = exp

                frame = self.camera.capture_frame()
                if frame is not None:
                    captured_data.append({"frame_data": frame, "wavelength": wavelength, "exposure_us": exp})

                prev_wavelength = wavelength

            # Zapisywanie kafelka do pliku TIFF
            if captured_data:
                filename = f"tile_{tile_idx:03d}_X{dx:.2f}_Y{dy:.2f}.tiff"
                full_path = os.path.join(mosaic_dir, filename)

                pil_images = [Image.fromarray(item["frame_data"]) for item in captured_data]
                pil_images[0].save(full_path, save_all=True, append_images=pil_images[1:])

                metadata_tiles.append({
                    "tile_index": tile_idx,
                    "filename": filename,
                    "relative_x": dx,
                    "relative_y": dy
                })

        # Zapis pliku JSON z metadanymi mozaiki
        with open(os.path.join(mosaic_dir, "mosaic_layout.json"), "w") as f:
            json.dump({
                "sample_width": sample_w, "sample_height": sample_h,
                "fov_x": fov_x, "fov_y": fov_y, "overlap": overlap,
                "tiles": metadata_tiles
            }, f, indent=4)

            # Powrót na środek po zakończeniu skanowania
            print("\n[INFO] Skanowanie fizyczne zakończone. Wracam na środek...")
            platform.move_to_position_blocking(center_x, center_y)

            # Automatyczne zszywanie mozaiki
            print("[INFO] Rozpoczynam automatyczne zszywanie kafelków do hiperkostki...")
            try:
                stitcher = MosaicStitcher(mosaic_dir)
                success = stitcher.stitch("finalna_hiperkostka_mozaika.tiff")

                if success:
                    print(f"[INFO] SUKCES! Zszyta hiperkostka znajduje się w folderze: {mosaic_dir}")
                else:
                    print("[INFO] BŁĄD: Proces zszywania zakończył się niepowodzeniem.")
            except Exception as e:
                print(f"[INFO] KRYTYCZNY BŁĄD ZSZYWANIA: {e}")

            self.is_scanning = False
            print("[INFO] Wszystkie zadania gotowe. Możesz używać systemu.")

    def cleanup(self):
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()