import json
import math
import os
import time

import numpy as np
from PIL import Image

from hardware.camera import ThorlabsCamera
from hardware.KURIOS_COMMAND_LIB import Kurios
import core.focus_stacker as focus_stacker
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
        self.bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}
        self.image_format = (".tiff", ".jpg", ".png")

        self.exposure_times = self._load_json("source/data/exposure_times.json")
        self.tuning_times = self._load_json("source/data/tuning_times.json")

    def _load_json(self, path):
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, path)

        if not os.path.exists(path):
            print(f"[INFO] Plik konfiguracyjny {path} nie zostal znaleziony.")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[INFO] Blad podczas ladowania {path}: {e}")
            return {}

    def _get_exposure_time(self, bandwidth_mode, step, wavelength):
        mode_data = self.exposure_times.get(bandwidth_mode, {})
        step_data = mode_data.get(str(step), mode_data)
        return step_data.get(str(wavelength), 10000)

    def _get_tuning_delay_ms(self, bandwidth_mode, step, prev_wavelength, wavelength):
        mode_data = self.tuning_times.get(bandwidth_mode, {})
        step_data = mode_data.get(str(step), mode_data)
        transition_key = f"{prev_wavelength},{wavelength}"
        return step_data.get(transition_key, step_data.get(str(wavelength), 200))

    def connect_hardware(self):
        print("[INFO] Connecting hardware...")

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

    def if_safe_to_scan(self) -> bool:
        if not self.camera or not self.filter:
            return False

        if self.is_scanning:
            return False

        return True

    def capture_image(self, wavelength, exposure, gain, bandwidth_name, bandwidth_code, save_path=None, image_format=".tiff"):
        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna przechwycic obrazu. Upewnij sie, ze sprzet jest polaczony i nie trwa inne skanowanie.")
            return None

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
        frame = self.camera.capture_frame()

        if save_path is None:
            return frame

        if frame is not None:
            filename = f"manual_{wavelength}nm_{bandwidth_name}{image_format}"
            full_path = os.path.join(save_path, filename)

            if image_format.lower() in [".png", ".jpg", ".jpeg"]:
                bit_depth = self.camera.camera.bit_depth if self.camera else 10
                frame = (frame >> (bit_depth - 8)).astype(np.uint8)
            else:
                frame = frame.astype(np.uint16)

            Image.fromarray(frame).save(full_path)
            print(f"[CAM] Zapisano zdjecie: {full_path}")

        return None

    def set_hardware_params(self, wavelength, exposure, bandwidth_name, gain):
        """Updating filter and camera parameters based on the provided values."""
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
        return None

    def stop_live_view(self):
        if self.camera and self.camera_connected:
            self.camera.stop_live_view()

    def scan_sequence(self, starting_wavelength, ending_wavelength, step, bandwidth_mode, gain):
        """
        Performs only the spectral photo sequence.

        This function intentionally does not move the platform, create maps,
        perform focus stacking, save mosaic tiles, or run stitching. Higher-level
        acquisition flows should call this function when they need one spectral
        stack from the current XY/Z position.
        """
        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna rozpoczac skanowania. Upewnij sie, ze sprzet jest polaczony i nie trwa inne skanowanie.")
            return None

        self.is_scanning = True
        try:
            bandwidth_code = self.bandwidth_modes.get(bandwidth_mode, 4)
            self.filter.SetBandwidthMode(bandwidth_code)
            self.filter.SetOutputMode(1)
            time.sleep(0.2)

            try:
                if hasattr(self.camera.camera, "gain"):
                    self.camera.camera.gain = gain
                elif hasattr(self.camera.camera, "analog_gain"):
                    self.camera.camera.analog_gain = gain
            except Exception as e:
                print(f"[CAM] Gain nie mogl zostac ustawiony dla skanowania: {e}")

            wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))
            prev_wavelength = wavelengths[0]
            captured_data = []

            for i, wavelength in enumerate(wavelengths):
                self.filter.SetWavelength(wavelength)

                if i > 0:
                    delay_ms = self._get_tuning_delay_ms(bandwidth_mode, step, prev_wavelength, wavelength)
                    time.sleep(delay_ms / 1000.0)
                else:
                    time.sleep(0.2)

                exposure_time = self._get_exposure_time(bandwidth_mode, step, wavelength)
                self.camera.camera.exposure_time_us = exposure_time

                frame = self.camera.capture_frame()
                if frame is not None:
                    captured_data.append({
                        "frame_data": frame,
                        "wavelength": wavelength,
                        "exposure_us": exposure_time
                    })
                    print(f"[CAM] Przechwycono klatke {i + 1}/{len(wavelengths)} dla {wavelength}nm (ekspozycja: {exposure_time} us)")
                else:
                    print(f"[CAM] Blad: Nie udalo sie przechwycic klatki dla {wavelength}nm")

                prev_wavelength = wavelength

            return captured_data
        finally:
            self.is_scanning = False

    def hypercube_scan(self, starting_wavelength, ending_wavelength, step, bandwidth_mode, gain,
                       save_path, image_format=".tiff"):
        captured_data = self.scan_sequence(starting_wavelength, ending_wavelength, step, bandwidth_mode, gain)

        if captured_data:
            self.save_hypercube(
                captured_data=captured_data,
                starting_wavelength=starting_wavelength,
                ending_wavelength=ending_wavelength,
                step=step,
                bandwidth_mode=bandwidth_mode,
                gain=gain,
                save_path=save_path,
                image_format=image_format
            )

    def focus_stack(self, platform, bottom_height, top_height, num_of_frames,
                    hypercube_scanning=False, starting_wavelength=None, ending_wavelength=None, step=None,
                    bandwidth_mode=None, gain=None, save_path=None, image_format=".tiff"):
        if not self.if_safe_to_scan():
            print("[INFO] Zablokowano sprzet. Trwa inne skanowanie.")
            return None
        if num_of_frames <= 1:
            print("[INFO] Potrzeba przynajmniej 2 klatek do focus stackingu.")
            return None

        self.is_scanning = True
        try:
            frames = []
            z_step = (top_height - bottom_height) / (num_of_frames - 1)

            for i in range(num_of_frames):
                self.is_scanning = False

                if hypercube_scanning:
                    frame_data = self.scan_sequence(starting_wavelength, ending_wavelength, step, bandwidth_mode, gain)
                    frames.append(frame_data)
                else:
                    exposure_time = self._get_exposure_time(bandwidth_mode, step or 10, starting_wavelength)
                    frame = self.capture_image(
                        starting_wavelength,
                        exposure_time,
                        gain,
                        bandwidth_mode,
                        self.bandwidth_modes.get(bandwidth_mode, 4)
                    )
                    frames.append(frame)

                self.is_scanning = True

                if i < num_of_frames - 1:
                    platform.validate_and_move("Z", z_step, -1)

            stacked_result = focus_stacker.stack(frames, hypercube_scanning)

            if save_path:
                if hypercube_scanning:
                    self.save_hypercube(
                        captured_data=stacked_result,
                        starting_wavelength=starting_wavelength,
                        ending_wavelength=ending_wavelength,
                        step=step,
                        bandwidth_mode=bandwidth_mode,
                        gain=gain,
                        save_path=save_path,
                        image_format=image_format
                    )
                else:
                    filename = f"stacked_{starting_wavelength}nm_{bandwidth_mode}{image_format}"
                    full_path = os.path.join(save_path, filename)

                    if image_format.lower() in [".png", ".jpg", ".jpeg"]:
                        bit_depth = self.camera.camera.bit_depth if self.camera else 10
                        stacked_result = (stacked_result >> (bit_depth - 8)).astype(np.uint8)
                    else:
                        stacked_result = stacked_result.astype(np.uint16)

                    Image.fromarray(stacked_result).save(full_path)
                    print(f"[CAM] Zapisano zdjecie focus stack: {full_path}")

            return stacked_result
        finally:
            self.is_scanning = False

    def generate_scan_grid(self, sample_width, sample_height, fov_x, fov_y, overlap_percent):
        if fov_x <= 0 or fov_y <= 0 or sample_width <= 0 or sample_height <= 0:
            print("[INFO] Bledne wymiary FOV lub probki. Zwracam pusta siatke.")
            return []

        overlap_factor = overlap_percent / 100.0
        step_x = fov_x * (1.0 - overlap_factor)
        step_y = fov_y * (1.0 - overlap_factor)

        if step_x <= 0 or step_y <= 0:
            print("[INFO] Bledna zakladka. Krok siatki musi byc wiekszy od zera.")
            return []

        cols = max(1, math.ceil(sample_width / step_x))
        rows = max(1, math.ceil(sample_height / step_y))

        offset_x = ((cols - 1) * step_x) / 2.0
        offset_y = ((rows - 1) * step_y) / 2.0

        grid_points = []
        for r in range(rows):
            y = (r * step_y) - offset_y
            col_range = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)

            for c in col_range:
                x = (c * step_x) - offset_x
                grid_points.append((x, y))

        print(f"[INFO] Wygenerowano siatke: {cols}x{rows} ({len(grid_points)} pkt).")
        return grid_points

    def _perform_mapped_scan(self, platform, save_path, sample_width, sample_height, fov_x, fov_y, overlap,
                             acquisition_function, save_function, layout_params,
                             dir_prefix, stitch_filename, stitch_after=True):
        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna rozpoczac mapowania. Upewnij sie, ze sprzet jest polaczony.")
            return None

        if not platform.grbl.ser or not platform.grbl.ser.is_open:
            print("[INFO] Najpierw polacz platforme!")
            return None

        if not platform.is_ready:
            print("[INFO] Platforma nie jest gotowa. Wykonaj Homing lub Unlock.")
            return None

        grid_points = self.generate_scan_grid(sample_width, sample_height, fov_x, fov_y, overlap)
        if not grid_points:
            return None

        center_x, center_y = platform.x_state, platform.y_state
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mosaic_dir = os.path.join(save_path, f"{dir_prefix}_{timestamp}")
        os.makedirs(mosaic_dir, exist_ok=True)

        metadata_tiles = []
        self.is_scanning = True
        try:
            print(f"[INFO] Rozpoczynam mapowanie ({dir_prefix}). Srodek probki: X={center_x:.2f}, Y={center_y:.2f}")

            for tile_idx, (dx, dy) in enumerate(grid_points):
                target_x, target_y = center_x + dx, center_y + dy
                print(f"\n[SCAN] --- Kafelek {tile_idx + 1}/{len(grid_points)} --- X={target_x:.2f}, Y={target_y:.2f}")

                if not platform.move_to_position_blocking(target_x, target_y):
                    print(f"[SCAN] Pomijam kafelek {tile_idx}, bo ruch platformy sie nie powiodl.")
                    continue

                self.is_scanning = False
                captured_data = acquisition_function()
                self.is_scanning = True

                if captured_data is None or (isinstance(captured_data, list) and not captured_data):
                    print(f"[SCAN] Brak danych dla kafelka {tile_idx}.")
                    continue

                filename = f"tile_{tile_idx:03d}_X{dx:.2f}_Y{dy:.2f}.tiff"
                full_path = os.path.join(mosaic_dir, filename)
                save_function(captured_data, full_path)

                metadata_tiles.append({"tile_index": tile_idx, "filename": filename, "relative_x": dx, "relative_y": dy, "absolute_x": target_x, "absolute_y": target_y})

            self._save_mosaic_layout(mosaic_dir=mosaic_dir, sample_width=sample_width, sample_height=sample_height, fov_x=fov_x, fov_y=fov_y, overlap=overlap, tiles=metadata_tiles, **layout_params)

            print(f"\n[INFO] Mapowanie zakonczone. Wracam na srodek probki...")
            platform.move_to_position_blocking(center_x, center_y)

            if stitch_after and metadata_tiles:
                print("[INFO] Rozpoczynam automatyczne zszywanie kafelkow...")
                stitcher = MosaicStitcher(mosaic_dir)
                if stitcher.stitch(stitch_filename):
                    print(f"[INFO] Zszyta mozaika znajduje sie w folderze: {mosaic_dir}")
                else:
                    print("[INFO] Zszywanie zakonczylo sie niepowodzeniem.")

            return mosaic_dir
        except Exception as e:
            print(f"[INFO] Krytyczny blad mapowania: {e}")
            return None
        finally:
            self.is_scanning = False

    def mapped_hypercube_scan(self, platform, save_path, starting_wavelength, ending_wavelength, step,
                              bandwidth_mode, gain, sample_width, sample_height, fov_x, fov_y, overlap,
                              image_format=".tiff", focus_stack_params=None, stitch_after=True):
        def acquisition_function():
            if focus_stack_params:
                initial_z = platform.z_state
                data = self.focus_stack(
                    platform=platform,
                    bottom_height=focus_stack_params["bottom_height"],
                    top_height=focus_stack_params["top_height"],
                    num_of_frames=focus_stack_params["num_frames"],
                    hypercube_scanning=True,
                    starting_wavelength=starting_wavelength,
                    ending_wavelength=ending_wavelength,
                    step=step,
                    bandwidth_mode=bandwidth_mode,
                    gain=gain,
                    save_path=None,
                    image_format=image_format
                )
                z_delta = initial_z - platform.z_state
                if z_delta != 0:
                    platform.validate_and_move("Z", abs(z_delta), 1 if z_delta > 0 else -1)
                return data
            else:
                return self.scan_sequence(starting_wavelength, ending_wavelength, step, bandwidth_mode, gain)

        layout_params = {
            "starting_wavelength": starting_wavelength,
            "ending_wavelength": ending_wavelength,
            "step": step,
            "bandwidth_mode": bandwidth_mode,
            "gain": gain,
            "focus_stack_params": focus_stack_params
        }

        return self._perform_mapped_scan(
            platform=platform,
            save_path=save_path,
            sample_width=sample_width,
            sample_height=sample_height,
            fov_x=fov_x,
            fov_y=fov_y,
            overlap=overlap,
            acquisition_function=acquisition_function,
            save_function=self._save_tile_hypercube,
            layout_params=layout_params,
            dir_prefix="Mosaic",
            stitch_filename="final_hypercube_mosaic.tiff",
            stitch_after=stitch_after
        )

    def run_acquisition(self, platform, save_path, spectral_scan, mapping, focus_stack_params,
                        wavelength=None, exposure=None, starting_wavelength=None, ending_wavelength=None,
                        step=None, bandwidth_mode=None, gain=0.0, bandwidth_code=None,
                        sample_width=None, sample_height=None, fov_x=None, fov_y=None, overlap=None,
                        image_format=".tiff"):
        if spectral_scan:
            if mapping:
                return self.mapped_hypercube_scan(
                    platform=platform,
                    save_path=save_path,
                    starting_wavelength=starting_wavelength,
                    ending_wavelength=ending_wavelength,
                    step=step,
                    bandwidth_mode=bandwidth_mode,
                    gain=gain,
                    sample_width=sample_width,
                    sample_height=sample_height,
                    fov_x=fov_x,
                    fov_y=fov_y,
                    overlap=overlap,
                    image_format=image_format,
                    focus_stack_params=focus_stack_params
                )

            if focus_stack_params:
                return self.focus_stack(
                    platform,
                    focus_stack_params["bottom_height"],
                    focus_stack_params["top_height"],
                    focus_stack_params["num_frames"],
                    True,
                    starting_wavelength,
                    ending_wavelength,
                    step,
                    bandwidth_mode,
                    gain,
                    save_path,
                    image_format
                )

            return self.hypercube_scan(
                starting_wavelength,
                ending_wavelength,
                step,
                bandwidth_mode,
                gain,
                save_path,
                image_format
            )

        if mapping:
            return self.mapped_capture_image(
                platform=platform,
                save_path=save_path,
                wavelength=wavelength,
                exposure=exposure,
                gain=gain,
                bandwidth_name=bandwidth_mode,
                sample_width=sample_width,
                sample_height=sample_height,
                fov_x=fov_x,
                fov_y=fov_y,
                overlap=overlap,
                image_format=image_format,
                focus_stack_params=focus_stack_params
            )

        if focus_stack_params:
            return self.focus_stack(
                platform,
                focus_stack_params["bottom_height"],
                focus_stack_params["top_height"],
                focus_stack_params["num_frames"],
                False,
                wavelength,
                wavelength,
                step or 10,
                bandwidth_mode,
                gain,
                save_path,
                image_format
            )

        if bandwidth_code is None:
            bandwidth_code = self.bandwidth_modes.get(bandwidth_mode, 4)

        return self.capture_image(
            wavelength,
            exposure,
            gain,
            bandwidth_mode,
            bandwidth_code,
            save_path,
            image_format
        )

    def mapped_capture_image(self, platform, save_path, wavelength, exposure, gain, bandwidth_name,
                             sample_width, sample_height, fov_x, fov_y, overlap,
                             image_format=".tiff", focus_stack_params=None, stitch_after=True):
        bandwidth_code = self.bandwidth_modes.get(bandwidth_name, 4)

        def acquisition_function():
            if focus_stack_params:
                initial_z = platform.z_state
                frame = self.focus_stack(
                    platform=platform,
                    bottom_height=focus_stack_params["bottom_height"],
                    top_height=focus_stack_params["top_height"],
                    num_of_frames=focus_stack_params["num_frames"],
                    hypercube_scanning=False,
                    starting_wavelength=wavelength,
                    ending_wavelength=wavelength,
                    step=10,
                    bandwidth_mode=bandwidth_name,
                    gain=gain,
                    save_path=None,
                    image_format=image_format
                )
                z_delta = initial_z - platform.z_state
                if z_delta != 0:
                    platform.validate_and_move("Z", abs(z_delta), 1 if z_delta > 0 else -1)
                return frame
            else:
                return self.capture_image(wavelength, exposure, gain, bandwidth_name, bandwidth_code, save_path=None, image_format=image_format)

        layout_params = {
            "starting_wavelength": wavelength,
            "ending_wavelength": wavelength,
            "step": 0,
            "bandwidth_mode": bandwidth_name,
            "gain": gain,
            "focus_stack_params": focus_stack_params
        }

        return self._perform_mapped_scan(
            platform=platform,
            save_path=save_path,
            sample_width=sample_width,
            sample_height=sample_height,
            fov_x=fov_x,
            fov_y=fov_y,
            overlap=overlap,
            acquisition_function=acquisition_function,
            save_function=self._save_tile_frame,
            layout_params=layout_params,
            dir_prefix="Mapping",
            stitch_filename="final_image_mosaic.tiff",
            stitch_after=stitch_after
        )

    def _save_tile_hypercube(self, captured_data, full_path):
        pil_images = [Image.fromarray(item["frame_data"].astype(np.uint16)) for item in captured_data]
        pil_images[0].save(full_path, save_all=True, append_images=pil_images[1:])
        print(f"[CAM] Zapisano kafelek hypercube: {full_path}")

    def _save_tile_frame(self, frame, full_path):
        Image.fromarray(frame.astype(np.uint16)).save(full_path)
        print(f"[CAM] Zapisano kafelek: {full_path}")

    def _save_mosaic_layout(self, mosaic_dir, sample_width, sample_height, fov_x, fov_y, overlap, tiles,
                            starting_wavelength, ending_wavelength, step, bandwidth_mode, gain,
                            focus_stack_params=None):
        layout = {
            "sample_width": sample_width,
            "sample_height": sample_height,
            "fov_x": fov_x,
            "fov_y": fov_y,
            "overlap": overlap,
            "scan_parameters": {
                "start_wavelength_nm": starting_wavelength,
                "end_wavelength_nm": ending_wavelength,
                "step_nm": step,
                "bandwidth_mode": bandwidth_mode,
                "gain": gain,
                "focus_stack": focus_stack_params
            },
            "tiles": tiles
        }

        with open(os.path.join(mosaic_dir, "mosaic_layout.json"), "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=4)

    def save_hypercube(self, captured_data, starting_wavelength, ending_wavelength, step, bandwidth_mode, gain,
                       save_path, image_format):
        if not captured_data:
            return

        frame_metadata_list = {}
        for i, item in enumerate(captured_data):
            frame_metadata_list[i] = {
                "wavelength_nm": item["wavelength"],
                "exposure_us": item["exposure_us"]
            }

        scan_parameters = {
            "start_wavelength_nm": starting_wavelength,
            "end_wavelength_nm": ending_wavelength,
            "step_nm": step,
            "bandwidth_mode": bandwidth_mode,
            "gain": gain
        }

        full_metadata = {
            "software": "Multispectral Imaging System",
            "scan_parameters": scan_parameters,
            "frames": frame_metadata_list
        }
        metadata_json_string = json.dumps(full_metadata, indent=4)

        filename = f"scan_{starting_wavelength}-{ending_wavelength}nm_step{step}_{bandwidth_mode}"

        if image_format.lower() in [".png", ".jpg", ".jpeg"]:
            bit_depth = self.camera.camera.bit_depth

            for item in captured_data:
                wavelength = item["wavelength"]
                file_path = os.path.join(save_path, f"{filename}_{wavelength}nm{image_format}")
                frame_data = (item["frame_data"] >> (bit_depth - 8)).astype(np.uint8)
                Image.fromarray(frame_data).save(file_path)
        else:
            pil_images = [Image.fromarray(item["frame_data"].astype(np.uint16)) for item in captured_data]
            full_path = os.path.join(save_path, f"{filename}{image_format}")

            pil_images[0].save(
                full_path,
                save_all=True,
                append_images=pil_images[1:],
                description=metadata_json_string
            )
            print(f"[CAM] Zapisano plik hypercube (wielostronicowy TIFF): {full_path}")

    def cleanup(self):
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()
