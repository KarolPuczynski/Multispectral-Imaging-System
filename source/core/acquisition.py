import time
import json
import os
from hardware.camera import ThorlabsCamera
from PIL import Image
import numpy as np

from hardware.KURIOS_COMMAND_LIB import Kurios
import core.focus_stacker as focus_stacker

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
        
        self.image_format = (".tiff", ".jpg", ".png")

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
            self.camera = ThorlabsCamera(self.manual_exposure)
            self.camera_connected = True
            print("[CAM] Kamera połączona.")

            self.filter = Kurios()

            devices = self.filter.list_devices()
            if not devices:
                print("[CAM] Błąd: Nie znaleziono urządzenia KURIOS na USB.")
                self.kurios_connected = False
                return False

            serial_port = devices[0][0]
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
    
    def if_safe_to_scan(self) -> bool:
        if not self.camera or not self.filter:
            return False

        if self.is_scanning:
            return False

        return True

    def capture_image(self, wavelength, exposure, gain, bandwidth_name, bandwidth_code, save_path=None, image_format=".tiff"):
        if not self.if_safe_to_scan():
            print("[INFO] Nie można przechwycić obrazu. Upewnij się, że sprzęt jest połączony i nie trwa inne skanowanie.")
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

        if save_path is None:
            frame = self.camera.capture_frame()
            return frame
        else:
            filename = f"manual_{wavelength}nm_{bandwidth_name}{image_format}"
            full_path = os.path.join(save_path, filename)
            
            frame = self.camera.capture_frame()
            if frame is not None:
                # Jeśli format to JPG/PNG, robimy przesunięcie bitowe do 8-bit
                if image_format.lower() in [".png", ".jpg", ".jpeg"]:
                    bit_depth = self.camera.camera.bit_depth if self.camera else 10
                    frame = (frame >> (bit_depth - 8)).astype(np.uint8)
                else:
                    frame = frame.astype(np.uint16)
                    
                Image.fromarray(frame).save(full_path)
                print(f"[CAM] Zapisano zdjęcie: {full_path}")
            return None

    def set_hardware_params(self, wavelength, exposure, bandwidth_name, gain):
        """Updating filter and camera parameters based on the provided values"""
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

    def scan_sequence(self, starting_wavelength, ending_wavelength, step, bandwidth_mode, gain):
        """
        This func is responsible for performing a full scan sequence of the sample.

        args:
            - save_path: directory where the resulting TIFF file will be saved
            - starting_wavelength: the wavelength at which the scan will start (in nm)
            - ending_wavelength: the wavelength at which the scan will end (in nm)
            - step: the step size for wavelength changes (in nm)
            - mode: the bandwidth mode for the filter ("Wide", "Medium", "Narrow", "Black")
            - gain: the gain value to set on the camera for the entire scan

        returns:
            - captured_data: a list of dictionaries containing the captured frame data and metadata for each wavelength
        """


        if not self.if_safe_to_scan():
            print("[INFO] Nie można rozpocząć skanowania. Upewnij się, że sprzęt jest połączony i nie trwa inne skanowanie.")
            return

        self.is_scanning = True        

        # Hardware setup
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
            print(f"[CAM] Gain nie mógł zostać ustawiony dla skanowania: {e}")


        wavelengths = list(range(starting_wavelength, ending_wavelength + 1, step))
        prev_wavelength = wavelengths[0]

        captured_data = []

        # Scan sequence loop
        for i, wavelength in enumerate(wavelengths):
            # Set wavelength on the filter
            self.filter.SetWavelength(wavelength)

            # Delay between wavelength changes to allow the filter to stabilize
            if i > 0:
                # accessing tuning times from tuning_times.JSON 
                key = f"{prev_wavelength},{wavelength}"
                delay_ms = self.tuning_times.get(bandwidth_mode, {}).get(key, 200)
                time.sleep(delay_ms / 1000.0)
            else:
                time.sleep(0.2)

            # Set exposure time on the camera based on the current wavelength and bandwidth mode
            exposure_time = self.exposure_times.get(bandwidth_mode, {}).get(str(wavelength), 10000)
            self.camera.camera.exposure_time_us = exposure_time

            # Capture frame
            frame = self.camera.capture_frame()
            if frame is not None:
                frame_info = {
                    "frame_data": frame,
                    "wavelength": wavelength,
                    "exposure_us": exposure_time
                }
                captured_data.append(frame_info)
                print(f"[CAM] Przechwycono klatkę {i+1}/{len(wavelengths)} dla {wavelength}nm (ekspozycja: {exposure_time} µs)")
            else:
                print(f"[CAM] Błąd: Nie udało się przechwycić klatki dla {wavelength}nm")

            # Update prev_wavelength for the next iteration
            prev_wavelength = wavelength

        return captured_data

    def hypercube_scan(self, starting_wavelength, ending_wavelength, step, bandwidth_mode, gain, 
                       save_path, image_format=".tiff"):

        # Capture the scan sequence frames and data
        captured_data = self.scan_sequence(starting_wavelength, ending_wavelength, step, bandwidth_mode, gain)

        # Save the captured data as
        if captured_data:
            filename = f"scan_{starting_wavelength}-{ending_wavelength}nm_step{step}_{bandwidth_mode}.tiff"
            self.save_hypercube(
                captured_data=captured_data,
                filename=filename,
                starting_wavelength=starting_wavelength,
                ending_wavelength=ending_wavelength,
                step=step,
                bandwidth_mode=bandwidth_mode,
                gain=gain,
                save_path=save_path,
                image_format=image_format
            )

        self.is_scanning = False

    def focus_stack(self, platform, bottom_height, top_height, num_of_frames, 
                    hypercube_scanning=False, starting_wavelength=None, ending_wavelength=None, step=None, bandwidth_mode=None, gain=None,
                    save_path=None, image_format=".tiff"):
        
        if not self.if_safe_to_scan():
            print("[INFO] Zablokowano sprzęt. Trwa inne skanowanie.")
            return None
        if num_of_frames <= 1:
            print("[INFO] Potrzeba przynajmniej 2 klatek do focus stackingu.")
            return None

        self.is_scanning = True
        try:
            frames = []
            z_step = (top_height - bottom_height) / (num_of_frames - 1)
            
            # Collect frames for focus stacking
            for i in range(num_of_frames):
                self.is_scanning = False

                if hypercube_scanning:
                    frame_data = self.scan_sequence(starting_wavelength, ending_wavelength, step, bandwidth_mode, gain)
                    frames.append(frame_data)

                else:
                    exposure_time = self.exposure_times.get(bandwidth_mode, {}).get(str(starting_wavelength), 10000)
                    frame = self.capture_image(starting_wavelength, exposure_time, gain, bandwidth_mode, self.bandwidth_modes.get(bandwidth_mode, 4))
                    frames.append(frame)

                self.is_scanning = True
                
                # Move the platform to the next Z position
                if i < num_of_frames - 1:
                    platform.validate_and_move('Z', z_step, -1)

            # Perform focus stacking on the collected frames
            stacked_result = focus_stacker.stack(frames, hypercube_scanning)

            # Save the stacked result
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