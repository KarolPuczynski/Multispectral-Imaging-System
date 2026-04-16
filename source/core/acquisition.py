import json
import math
import os
import time

from PIL import Image

from core.stitching import MosaicStitcher
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
        self.bandwidth_modes = {
            "Wide": 2,
            "Medium": 4,
            "Narrow": 8,
        }

        self.exposure_times = self._load_json("data/exposure_times.json")
        self.tuning_times = self._load_json("data/tuning_times.json")

    def _load_json(self, path):
        if not os.path.exists(path):
            print(f"[INFO] Plik konfiguracyjny {path} nie zostal znaleziony.")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[INFO] Blad podczas ladowania {path}: {e}")
            return {}

    def connect_hardware(self):
        print("[INFO] Laczenie ze sprzetem...")

        if self.is_scanning:
            print("[INFO] Nie mozna laczyc urzadzen podczas skanowania!")
            return False

        try:
            self.camera = ThorlabsCamera(self.manual_exposure)
            self.camera_connected = True
            print("[CAM] Kamera polaczona.")

            self.filter = Kurios()
            devices = self.filter.list_devices()
            if not devices:
                print("[CAM] Blad: Nie znaleziono urzadzenia KURIOS na USB.")
                self.kurios_connected = False
                return False

            serial_port = devices[0][0]
            status = self.filter.open(serial_port, 115200, 1)

            if status >= 0:
                self.kurios_connected = True
                print(f"[CAM] KURIOS polaczony na porcie: {serial_port}")
            else:
                print("[CAM] Blad: Nie udalo sie otworzyc portu KURIOS.")
                self.kurios_connected = False
                return False

        except Exception as e:
            print(f"[CAM] Krytyczny blad polaczenia: {e}")
            return False

        return True

    def capture_image(self, save_path, wavelength, exposure, gain, bandwidth_name, bandwidth_code):
        if not self.camera or not self.filter:
            print("[INFO] Najpierw polacz urzadzenia!")
            return

        if self.is_scanning:
            print("[INFO] Trwa skanowanie")
            return

        self.filter.SetWavelength(wavelength)
        self.filter.SetBandwidthMode(bandwidth_code)

        self.camera.camera.exposure_time_us = exposure
        try:
            if hasattr(self.camera.camera, "gain"):
                self.camera.camera.gain = gain
            elif hasattr(self.camera.camera, "analog_gain"):
                self.camera.camera.analog_gain = gain
        except Exception as e:
            print(f"[CAM] Gain nie mogl zostac ustawiony: {e}")

        time.sleep(0.3)

        filename = f"manual_{wavelength}nm_{bandwidth_name}.tiff"
        full_path = os.path.join(save_path, filename)
        self.camera.save_frame(full_path)
        print(f"[CAM] Zapisano zdjecie: {full_path}")

    def set_hardware_params(self, wavelength, exposure, bandwidth_name, gain):
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
            print("[INFO] Bledne wymiary FOV lub probki. Zwracam pusta siatke.")
            return []

        overlap_factor = overlap_percent / 100.0
        step_x = fov_x * (1.0 - overlap_factor)
        step_y = fov_y * (1.0 - overlap_factor)

        cols = max(1, math.ceil(sample_width / step_x))
        rows = max(1, math.ceil(sample_height / step_y))

        offset_x = ((cols - 1) * step_x) / 2.0
        offset_y = ((rows - 1) * step_y) / 2.0

        grid_points = []
        for row in range(rows):
            y = (row * step_y) - offset_y
            col_range = range(cols) if row % 2 == 0 else range(cols - 1, -1, -1)

            for col in col_range:
                x = (col * step_x) - offset_x
                grid_points.append((x, y))

        print(
            f"[INFO] Wygenerowano wysrodkowana siatke: {cols}x{rows} ({len(grid_points)} pkt). "
            f"Offset do rogu: X={-offset_x:.2f}, Y={-offset_y:.2f}"
        )
        return grid_points

    def create_mosaic_scan_plan(self, sample_w, sample_h, fov_x, fov_y, overlap):
        grid_points = self.generate_scan_grid(sample_w, sample_h, fov_x, fov_y, overlap)
        if not grid_points:
            return None

        return {
            "sample_width": sample_w,
            "sample_height": sample_h,
            "fov_x": fov_x,
            "fov_y": fov_y,
            "overlap": overlap,
            "grid_points": grid_points,
        }

    def _create_scan_directory(self, save_path):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mosaic_dir = os.path.join(save_path, f"Mosaic_{timestamp}")
        os.makedirs(mosaic_dir, exist_ok=True)
        return mosaic_dir

    def _prepare_scan_capture(self, mode, gain):
        bandwidth_name = mode
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)
        self.filter.SetOutputMode(1)
        self.filter.SetBandwidthMode(bandwidth_code)
        time.sleep(0.2)

        try:
            if hasattr(self.camera.camera, "gain"):
                self.camera.camera.gain = gain
            elif hasattr(self.camera.camera, "analog_gain"):
                self.camera.camera.analog_gain = gain
        except Exception:
            pass

        return bandwidth_name

    def _capture_tile_sequence(self, wavelengths, bandwidth_name):
        captured_data = []
        previous_wavelength = wavelengths[0]

        for index, wavelength in enumerate(wavelengths):
            self.filter.SetWavelength(wavelength)

            if index > 0:
                key = f"{previous_wavelength},{wavelength}"
                delay_ms = self.tuning_times.get(bandwidth_name, {}).get(key, 200)
                time.sleep(delay_ms / 1000.0)
            else:
                time.sleep(0.2)

            exposure = self.exposure_times.get(bandwidth_name, {}).get(str(wavelength), 10000)
            self.camera.camera.exposure_time_us = exposure

            frame = self.camera.capture_frame()
            if frame is not None:
                captured_data.append(
                    {
                        "frame_data": frame,
                        "wavelength": wavelength,
                        "exposure_us": exposure,
                    }
                )

            previous_wavelength = wavelength

        return captured_data

    def _save_sequence(self, captured_data, save_dir, filename):
        if not captured_data:
            return None

        full_path = os.path.join(save_dir, filename)
        pil_images = [Image.fromarray(item["frame_data"]) for item in captured_data]
        pil_images[0].save(full_path, save_all=True, append_images=pil_images[1:])
        return full_path

    def save_mosaic_layout(self, mosaic_dir, plan, metadata_tiles):
        with open(os.path.join(mosaic_dir, "mosaic_layout.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "sample_width": plan["sample_width"],
                    "sample_height": plan["sample_height"],
                    "fov_x": plan["fov_x"],
                    "fov_y": plan["fov_y"],
                    "overlap": plan["overlap"],
                    "tiles": metadata_tiles,
                },
                f,
                indent=4,
            )

    def stitch_mosaic(self, mosaic_dir, output_filename="finalna_hiperkostka_mozaika.tiff"):
        print("[INFO] Rozpoczynam automatyczne zszywanie kafelkow do hiperkostki...")
        try:
            stitcher = MosaicStitcher(mosaic_dir)
            stitch_success = stitcher.stitch(output_filename)

            if stitch_success:
                print(f"[INFO] SUKCES! Zszyta hiperkostka znajduje sie w folderze: {mosaic_dir}")
            else:
                print("[INFO] BLAD: Proces zszywania zakonczyl sie niepowodzeniem.")
            return stitch_success
        except Exception as e:
            print(f"[INFO] KRYTYCZNY BLAD ZSZYWANIA: {e}")
            return False

    def scan_sequence(
        self,
        save_path,
        starting_wavelength,
        ending_wavelength,
        step,
        mode,
        gain,
        filename="scan_sequence.tiff",
    ):
        if not self.camera or not self.filter:
            print("[INFO] Najpierw polacz urzadzenia optyczne!")
            return None
        if self.is_scanning:
            print("[INFO] Skanowanie juz trwa!")
            return None

        wavelengths = []
        captured_data = []
        saved_path = None

        self.is_scanning = True
        try:
            bandwidth_name = self._prepare_scan_capture(mode, gain)
            wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))
            captured_data = self._capture_tile_sequence(wavelengths, bandwidth_name)
            saved_path = self._save_sequence(captured_data, save_path, filename)
        finally:
            self.is_scanning = False
            print("[INFO] Seria zdjec zakonczona.")

        return {
            "save_path": saved_path,
            "filename": filename,
            "wavelengths": wavelengths,
            "frames_captured": len(captured_data),
        }

    def run_mosaic_scan(
        self,
        platform,
        save_path,
        starting_wavelength,
        ending_wavelength,
        step,
        mode,
        gain,
        sample_w,
        sample_h,
        fov_x,
        fov_y,
        overlap,
    ):
        plan = self.create_mosaic_scan_plan(sample_w, sample_h, fov_x, fov_y, overlap)
        if not plan:
            return None

        if not self.camera or not self.filter:
            print("[INFO] Najpierw polacz urzadzenia optyczne!")
            return None
        if not platform.grbl.ser or not platform.grbl.ser.is_open:
            print("[INFO] Najpierw polacz platforme!")
            return None
        if self.is_scanning:
            print("[INFO] Skanowanie juz trwa!")
            return None

        self.is_scanning = True
        center_x = platform.x_state
        center_y = platform.y_state
        mosaic_dir = self._create_scan_directory(save_path)
        metadata_tiles = []

        try:
            for tile_idx, (dx, dy) in enumerate(plan["grid_points"]):
                target_x = center_x + dx
                target_y = center_y + dy

                print(
                    f"\n[SCAN] --- Kafelek {tile_idx + 1}/{len(plan['grid_points'])} --- "
                    f"(Ruch do X={target_x:.2f}, Y={target_y:.2f})"
                )

                success = platform.move_to_position_blocking(target_x, target_y)
                if not success:
                    print(f"[SCAN] Pomijam kafelek {tile_idx + 1}, aby uniknac kolizji z rama maszyny.")
                    continue

                self.is_scanning = False
                filename = f"tile_{tile_idx:03d}_X{dx:.2f}_Y{dy:.2f}.tiff"
                tile_result = self.scan_sequence(
                    save_path=mosaic_dir,
                    starting_wavelength=starting_wavelength,
                    ending_wavelength=ending_wavelength,
                    step=step,
                    mode=mode,
                    gain=gain,
                    filename=filename,
                )
                self.is_scanning = True

                if tile_result and tile_result["save_path"]:
                    metadata_tiles.append(
                        {
                            "tile_index": tile_idx,
                            "filename": filename,
                            "relative_x": dx,
                            "relative_y": dy,
                        }
                    )
        finally:
            print("\n[INFO] Skanowanie fizyczne zakonczone. Wracam na srodek...")
            platform.move_to_position_blocking(center_x, center_y)
            self.is_scanning = False
            print("[INFO] Cala sekwencja mozaiki zakonczona.")

        scan_result = {
            "mosaic_dir": mosaic_dir,
            "tiles": metadata_tiles,
            "center_x": center_x,
            "center_y": center_y,
            "scan_points": plan["grid_points"],
        }
        self.save_mosaic_layout(scan_result["mosaic_dir"], plan, scan_result["tiles"])
        scan_result["stitch_success"] = self.stitch_mosaic(scan_result["mosaic_dir"])
        return scan_result

    def cleanup(self):
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()
