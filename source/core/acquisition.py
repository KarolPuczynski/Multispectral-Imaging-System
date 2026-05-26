import json
import math
import os
import time
from dataclasses import dataclass, replace
from typing import Optional, Dict, Any

import numpy as np
from PIL import Image

from hardware.camera import ThorlabsCamera
from hardware.filter import Kurios
import core.focus_stacker as focus_stacker
from core.stitching import MosaicStitcher


@dataclass
class AcquisitionParams:
    """Data class to hold all parameters for an acquisition session."""
    save_path: Optional[str] = None
    image_format: str = ".tiff"
    
    # Filter and Camera settings
    wavelength: Optional[int] = 500
    exposure: Optional[int] = 50000
    gain: float = 0.0
    bandwidth_mode: Optional[str] = None
    bandwidth_code: Optional[int] = None
    bandwidth_modes = {"Wide": 2, "Medium": 4, "Narrow": 8}
    
    # Spectral Scan settings
    spectral_scan: bool = False
    starting_wavelength: Optional[int] = None
    ending_wavelength: Optional[int] = None
    step: Optional[int] = None
    
    # Mapping settings
    mapping: bool = False
    sample_width: Optional[float] = None
    sample_height: Optional[float] = None
    fov_x: Optional[float] = None
    fov_y: Optional[float] = None
    overlap: Optional[float] = None
    stitch_after: bool = True
    
    # Focus Stack
    focus_stack_params: Optional[Dict[str, Any]] = None


class Acquisition:
    """
    This class manages all interactions with the camera and filter for image acquisition, including:
    - Connecting to hardware
    - Capturing single frames or spectral sequences
    - Performing focus stacking
    - Generating scan grids for mapping
    It also handles saving captured data
    """
    def __init__(self):
        self.is_scanning = False
        self.camera = None
        self.filter = None
        self.camera_connected = False
        self.kurios_connected = False

        self.exposure_times = self._load_json("source/data/exposure_times.json")
        self.tuning_times = self._load_json("source/data/tuning_times.json")

    def _load_json(self, path):
        if not os.path.exists(path):
            print(f"[INFO] Plik {path} nie istnieje. Uzywam pustego slownika.")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_tuning_delay_ms(self, bandwidth_mode, step, prev_wavelength, wavelength):
        mode_data = self.tuning_times.get(bandwidth_mode, {})
        step_data = mode_data.get(str(step), mode_data)
        transition_key = f"{prev_wavelength},{wavelength}"
        return step_data.get(transition_key, step_data.get(str(wavelength), 200))

    def connect_hardware(self):
        """
        Attempts to connect to the camera and filter, setting up necessary parameters. Returns True if successful, False otherwise.
        """
        print("[INFO] Connecting hardware...")

        if self.is_scanning:
            print("[INFO] Nie mozna laczyc urzadzen podczas skanowania!")
            return False

        try:
            self.camera = ThorlabsCamera(1000)
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

    def capture_image(self, params: AcquisitionParams):
        """
        Captures a single image based on the provided params from gui.
        If save_path is provided, saves the image to disk. Otherwise, return the captured frame.
        """
        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna przechwycic obrazu. Upewnij sie, ze sprzet jest polaczony i nie trwa inne skanowanie.")
            return None

        self.filter.SetWavelength(params.wavelength)
        bandwidth_code = params.bandwidth_code if params.bandwidth_code is not None else params.bandwidth_modes.get(params.bandwidth_mode, 4)
        self.filter.SetBandwidthMode(bandwidth_code)

        self.camera.camera.exposure_time_us = params.exposure
        try:
            if hasattr(self.camera.camera, "gain"):
                self.camera.camera.gain = int(params.gain)
            elif hasattr(self.camera.camera, "analog_gain"):
                self.camera.camera.analog_gain = int(params.gain)
        except Exception as e:
            print(f"[CAM] Gain nie mogl zostac ustawiony: {e}")

        time.sleep(0.3)
        frame = self.camera.capture_frame()

        if params.save_path is None:
            return frame

        if frame is not None:
            filename = f"manual_{params.wavelength}nm_{params.bandwidth_mode}{params.image_format}"
            full_path = os.path.join(params.save_path, filename)

            if params.image_format.lower() in [".png", ".jpg", ".jpeg"]:
                bit_depth = self.camera.camera.bit_depth if self.camera else 10
                frame = (frame >> (bit_depth - 8)).astype(np.uint8)
            else:
                frame = frame.astype(np.uint16)

            Image.fromarray(frame).save(full_path)
            print(f"[CAM] Zapisano zdjecie: {full_path}")

        return None

    def set_hardware_params(self, params: AcquisitionParams):
        """Updating filter and camera parameters based on the provided values."""
        if self.filter and self.kurios_connected and params.bandwidth_mode is not None:
            bandwidth_code = params.bandwidth_modes.get(params.bandwidth_mode, 4)
            self.filter.SetWavelength(params.wavelength)
            self.filter.SetBandwidthMode(bandwidth_code)

        if self.camera and self.camera_connected and params.exposure is not None:
            self.camera.camera.exposure_time_us = params.exposure
            try:
                if hasattr(self.camera.camera, "gain"):
                    self.camera.camera.gain = int(params.gain)
                elif hasattr(self.camera.camera, "analog_gain"):
                    self.camera.camera.analog_gain = int(params.gain)
            except Exception:
                pass

    def start_live_view(self):
        if self.camera and self.camera_connected:
            return self.camera.start_live_view()
        return None

    def stop_live_view(self):
        if self.camera and self.camera_connected:
            self.camera.stop_live_view()

    def scan_sequence(self, params: AcquisitionParams):
        """
        Perform a spectral scan sequence based on the provided parameters.
        Returns a list of captured frames with metadata.
        """
        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna rozpoczac skanowania. Upewnij sie, ze sprzet jest polaczony i nie trwa inne skanowanie.")
            return None

        self.is_scanning = True
        try:
            bandwidth_code = params.bandwidth_code if params.bandwidth_code is not None else params.bandwidth_modes.get(params.bandwidth_mode, 4)
            self.filter.SetBandwidthMode(bandwidth_code)
            self.filter.SetOutputMode(1)
            time.sleep(0.2)

            try:
                if hasattr(self.camera.camera, "gain"):
                    self.camera.camera.gain = int(params.gain)
                elif hasattr(self.camera.camera, "analog_gain"):
                    self.camera.camera.analog_gain = int(params.gain)
            except Exception as e:
                print(f"[CAM] Gain nie mogl zostac ustawiony dla skanowania: {e}")

            # Calculate reference multiplier for exposure multiplication based on bandwidth mode and wavelength
            ref_multiplier = 1.0
            if params.bandwidth_mode in self.exposure_times:
                mode_data = self.exposure_times[params.bandwidth_mode]
                if str(params.wavelength) in mode_data:
                    ref_multiplier = mode_data[str(params.wavelength)]
            
            base_exposure = params.exposure / ref_multiplier

            wavelengths = list(range(params.starting_wavelength, params.ending_wavelength + 1, params.step))
            prev_wavelength = wavelengths[0]
            captured_data = []

            for i, wavelength in enumerate(wavelengths):
                self.filter.SetWavelength(wavelength)

                if i > 0:
                    delay_ms = self._get_tuning_delay_ms(params.bandwidth_mode, params.step, prev_wavelength, wavelength)
                    time.sleep(delay_ms / 1000.0)
                else:
                    time.sleep(0.2)

                multiplier = 1.0
                if params.bandwidth_mode in self.exposure_times:
                    mode_data = self.exposure_times[params.bandwidth_mode]
                    if str(wavelength) in mode_data:
                        multiplier = mode_data[str(wavelength)]
                        
                current_exposure = int(base_exposure * multiplier)
                self.camera.camera.exposure_time_us = current_exposure

                frame = self.camera.capture_frame()
                if frame is not None:
                    captured_data.append({
                        "frame_data": frame,
                        "wavelength": wavelength,
                        "exposure_us": current_exposure
                    })
                    print(f"[CAM] Przechwycono klatke {i + 1}/{len(wavelengths)} dla {wavelength}nm (ekspozycja: {current_exposure} us)")
                else:
                    print(f"[CAM] Blad: Nie udalo sie przechwycic klatki dla {wavelength}nm")

                prev_wavelength = wavelength

            return captured_data
        finally:
            self.is_scanning = False

    def hypercube_scan(self, params: AcquisitionParams):
        """Performs a spectral scan and saves the hypercube."""
        captured_data = self.scan_sequence(params)

        if captured_data:
            self.save_hypercube(
                captured_data=captured_data,
                params=params
            )

    def focus_stack(self, platform, params: AcquisitionParams):
        """
        Performs focus stacking by capturing multiple frames at different Z heights (by moving the platform in Z direction) 
        and combining them into one single sharp image.

        Returns: Focus stacked image
        """
        if not self.if_safe_to_scan():
            print("[INFO] Zablokowano sprzet. Trwa inne skanowanie.")
            return None
        if not params.focus_stack_params or params.focus_stack_params.get("num_frames", 0) <= 1:
            print("[INFO] Potrzeba przynajmniej 2 klatek do focus stackingu.")
            return None

        self.is_scanning = True
        try:
            frames = []
            num_of_frames = params.focus_stack_params["num_frames"]
            bottom_height = params.focus_stack_params["bottom_height"]
            top_height = params.focus_stack_params["top_height"]
            z_step = (top_height - bottom_height) / (num_of_frames - 1)

            cap_params = replace(params, save_path=None)

            for i in range(num_of_frames):
                self.is_scanning = False

                if params.spectral_scan:
                    frame_data = self.scan_sequence(cap_params)
                    if frame_data is not None:
                        frames.append(frame_data)
                else:
                    frame = self.capture_image(cap_params)
                    if frame is not None:
                        frames.append(frame)

                self.is_scanning = True

                if i < num_of_frames - 1:
                    platform.validate_and_move("Z", z_step, -1)

            if len(frames) < 2:
                print("[INFO] Zbyt malo poprawnych klatek do focus stackingu.")
                return frames[0] if frames else None

            stacked_result = focus_stacker.stack(frames, params.spectral_scan)

            if params.save_path and stacked_result is not None:
                if params.spectral_scan:
                    self.save_hypercube(
                        captured_data=stacked_result,
                        params=params
                    )
                else:
                    filename = f"stacked_{params.wavelength}nm_{params.bandwidth_mode}{params.image_format}"
                    full_path = os.path.join(params.save_path, filename)

                    if params.image_format.lower() in [".png", ".jpg", ".jpeg"]:
                        bit_depth = self.camera.camera.bit_depth if self.camera else 10
                        stacked_result = (stacked_result >> (bit_depth - 8)).astype(np.uint8)
                    else:
                        stacked_result = stacked_result.astype(np.uint16)

                    Image.fromarray(stacked_result).save(full_path)
                    print(f"[CAM] Zapisano zdjecie focus stack: {full_path}")

            return stacked_result
        finally:
            self.is_scanning = False

    def generate_scan_grid(self, params: AcquisitionParams):
        """
        Generates a list of (x, y) offsets for scanning based on the sample dimensions, FOV, and overlap.
        The grid is generated in a serpentine pattern to minimize travel time between points. 

        Returns a list of tuples with relative (x, y) positions for each tile in the scan grid.
        """
        if None in (params.fov_x, params.fov_y, params.sample_width, params.sample_height, params.overlap):
            print("[INFO] Brak pelnych wymiarow do wygenerowania siatki. Zwracam pusta siatke.")
            return []
            
        if params.fov_x <= 0 or params.fov_y <= 0 or params.sample_width <= 0 or params.sample_height <= 0:
            print("[INFO] Bledne wymiary FOV lub probki. Zwracam pusta siatke.")
            return []

        overlap_factor = params.overlap / 100.0
        step_x = params.fov_x * (1.0 - overlap_factor)
        step_y = params.fov_y * (1.0 - overlap_factor)

        if step_x <= 0 or step_y <= 0:
            print("[INFO] Bledna zakladka. Krok siatki musi byc wiekszy od zera.")
            return []

        cols = max(1, math.ceil(params.sample_width / step_x))
        rows = max(1, math.ceil(params.sample_height / step_y))

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

    def _perform_mapped_scan(self, platform, params: AcquisitionParams, acquisition_function, save_function, layout_params,
                             dir_prefix, stitch_filename):
        """
        Generalized function to perform a mapped scan (either spectral hypercube or single frame mapping) 
        by moving the platform to each position in the generated grid, acquiring data, and saving it.
        """

        if not self.if_safe_to_scan():
            print("[INFO] Nie mozna rozpoczac mapowania. Upewnij sie, ze sprzet jest polaczony.")
            return None

        if not platform.grbl.ser or not platform.grbl.ser.is_open:
            print("[INFO] Najpierw polacz platforme!")
            return None

        if not platform.is_ready:
            print("[INFO] Platforma nie jest gotowa. Wykonaj Homing lub Unlock.")
            return None

        grid_points = self.generate_scan_grid(params)
        if not grid_points:
            return None

        center_x, center_y = platform.x_state, platform.y_state
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mosaic_dir = os.path.join(params.save_path, f"{dir_prefix}_{timestamp}")
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

            self._save_mosaic_layout(mosaic_dir=mosaic_dir, sample_width=params.sample_width, sample_height=params.sample_height, fov_x=params.fov_x, fov_y=params.fov_y, overlap=params.overlap, tiles=metadata_tiles, **layout_params)

            print(f"\n[INFO] Mapowanie zakonczone. Wracam na srodek probki...")
            platform.move_to_position_blocking(center_x, center_y)

            if params.stitch_after and metadata_tiles:
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

    def mapped_hypercube_scan(self, platform, params: AcquisitionParams):
        """
        Performs a mapped spectral scan to create a hypercube mosaic by moving the platform across the sample in a grid pattern,
        capturing a spectral sequence at each position, and saving each tile as a multi-page TIFF. Also saves metadata about the scan layout.
        """
        def acquisition_function():
            if params.focus_stack_params:
                initial_z = platform.z_state
                fs_params = replace(params, save_path=None)
                data = self.focus_stack(platform, fs_params)
                z_delta = initial_z - platform.z_state
                if z_delta != 0:
                    platform.validate_and_move("Z", abs(z_delta), 1 if z_delta > 0 else -1)
                return data
            else:
                return self.scan_sequence(params)

        layout_params = {
            "starting_wavelength": params.starting_wavelength,
            "ending_wavelength": params.ending_wavelength,
            "step": params.step,
            "bandwidth_mode": params.bandwidth_mode,
            "gain": params.gain,
            "focus_stack_params": params.focus_stack_params
        }

        return self._perform_mapped_scan(
            platform=platform,
            params=params,
            acquisition_function=acquisition_function,
            save_function=self._save_tile_hypercube,
            layout_params=layout_params,
            dir_prefix="Mosaic",
            stitch_filename="final_hypercube_mosaic.tiff"
        )

    def run_acquisition(self, platform, params: AcquisitionParams):
        """
        Decides which acquisition method to run based on the provided parameters. It can perform:
        - A single image capture
        - A spectral hypercube scan
        - A focus stack
        - A mapped single image capture
        - A mapped spectral hypercube scan
        """
        if params.spectral_scan:
            if params.mapping:
                return self.mapped_hypercube_scan(platform, params)
            if params.focus_stack_params:
                return self.focus_stack(platform, params)
            return self.hypercube_scan(params)

        if params.mapping:
            return self.mapped_capture_image(platform, params)

        if params.focus_stack_params:
            return self.focus_stack(platform, params)

        if params.bandwidth_code is None:
            params.bandwidth_code = params.bandwidth_modes.get(params.bandwidth_mode, 4)

        return self.capture_image(params)

    def mapped_capture_image(self, platform, params: AcquisitionParams):
        """
        Performs a mapped acquisition of single frames across the sample by moving the platform in a grid pattern and capturing an image at each position.
        """
        params.bandwidth_code = params.bandwidth_modes.get(params.bandwidth_mode, 4)

        def acquisition_function():
            if params.focus_stack_params:
                initial_z = platform.z_state
                fs_params = replace(params, save_path=None)
                frame = self.focus_stack(platform=platform, params=fs_params)
                z_delta = initial_z - platform.z_state
                if z_delta != 0:
                    platform.validate_and_move("Z", abs(z_delta), 1 if z_delta > 0 else -1)
                return frame
            else:
                cap_params = replace(params, save_path=None)
                return self.capture_image(cap_params)

        layout_params = {
            "starting_wavelength": params.wavelength,
            "ending_wavelength": params.wavelength,
            "step": 0,
            "bandwidth_mode": params.bandwidth_mode,
            "gain": params.gain,
            "focus_stack_params": params.focus_stack_params
        }

        return self._perform_mapped_scan(
            platform=platform,
            params=params,
            acquisition_function=acquisition_function,
            save_function=self._save_tile_frame,
            layout_params=layout_params,
            dir_prefix="Mapping",
            stitch_filename="final_image_mosaic.tiff"
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

    def save_hypercube(self, captured_data, params: AcquisitionParams):
        if not captured_data:
            return

        frame_metadata_list = {}
        for i, item in enumerate(captured_data):
            frame_metadata_list[i] = {
                "wavelength_nm": item["wavelength"],
                "exposure_us": item["exposure_us"]
            }

        scan_parameters = {
            "start_wavelength_nm": params.starting_wavelength,
            "end_wavelength_nm": params.ending_wavelength,
            "step_nm": params.step,
            "bandwidth_mode": params.bandwidth_mode,
            "gain": params.gain
        }

        full_metadata = {
            "software": "Multispectral Imaging System",
            "scan_parameters": scan_parameters,
            "frames": frame_metadata_list
        }
        metadata_json_string = json.dumps(full_metadata, indent=4)

        filename = f"scan_{params.starting_wavelength}-{params.ending_wavelength}nm_step{params.step}_{params.bandwidth_mode}"

        if params.image_format.lower() in [".png", ".jpg", ".jpeg"]:
            bit_depth = self.camera.camera.bit_depth

            for item in captured_data:
                wavelength = item["wavelength"]
                file_path = os.path.join(params.save_path, f"{filename}_{wavelength}nm{params.image_format}")
                frame_data = (item["frame_data"] >> (bit_depth - 8)).astype(np.uint8)
                Image.fromarray(frame_data).save(file_path)
        else:
            pil_images = [Image.fromarray(item["frame_data"].astype(np.uint16)) for item in captured_data]
            full_path = os.path.join(params.save_path, f"{filename}{params.image_format}")

            pil_images[0].save(
                full_path,
                save_all=True,
                append_images=pil_images[1:],
                description=metadata_json_string
            )
            print(f"[CAM] Zapisano plik hypercube (wielostronicowy TIFF): {full_path}")

    def cleanup(self):
        """Closes connections to the camera and filter"""
        if self.camera is not None:
            self.camera.close()
        if self.filter is not None:
            self.filter.close()
