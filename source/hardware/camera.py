import numpy as np
import threading
import queue
from PIL import Image
import threading

try:
    from utilis.dll_loader import configure_path

    configure_path()
except ImportError:
    pass

from thorlabs_tsi_sdk.tl_camera import TLCameraSDK

DEFAULT_GAIN = 1

class ImageAcquisitionThread(threading.Thread):
    """
    Class inspired by Thorlabs example code for live view acquisition. 
    It runs in a separate thread to continuously poll the camera for new frames,
    processes them, and puts the resulting images into a queue for display in the live view widget.
    """
    def __init__(self, camera):
        super(ImageAcquisitionThread, self).__init__()
        self._camera = camera
        self._previous_timestamp = 0

        self._bit_depth = camera.bit_depth
        self._camera.image_poll_timeout_ms = 0
        self._image_queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

    def get_output_queue(self):
        return self._image_queue

    def stop(self):
        self._stop_event.set()

    def _get_image(self, frame):
        scaled_image = (frame.image_buffer >> (self._bit_depth - 8)).astype(np.uint8)
        return Image.fromarray(scaled_image)

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    pil_image = self._get_image(frame)
                    self._image_queue.put_nowait(pil_image)
            except queue.Full:
                pass
            except Exception as error:
                print(f"[CAM] Error in acquisition thread: {error}")
                break

        print("[CAM] Image acquisition thread stopped.")


class ThorlabsCamera:
    """
    Class responsible for managing the connection to the Thorlabs camera, 
    performing image captures, and handling live view functionality. 
    It uses the Thorlabs TSI SDK to interface with the camera hardware
    """
    def __init__(self, exposure_us=10000):
        self.sdk = TLCameraSDK()
        cameras = self.sdk.discover_available_cameras()
        if not cameras:
            raise RuntimeError("[CAM] Brak podłączonych kamer Thorlabs.")

        self.camera = self.sdk.open_camera(cameras[0])
        self.camera.exposure_time_us = exposure_us

        if hasattr(self.camera, "gain"):
            self.camera.gain = int(DEFAULT_GAIN)
        elif hasattr(self.camera, "analog_gain"):
            self.camera.analog_gain = int(DEFAULT_GAIN)

        self.live_thread = None
        self.is_live = False

        self._lock = threading.Lock()

        print(f"[CAM] Kamera gotowa: {cameras[0]} (ekspozycja: {exposure_us} µs)")

    def start_live_view(self):
        with self._lock:
            if self.is_live:
                return None

            print("[CAM] Uruchamianie Live View")
            self.camera.frames_per_trigger_zero_for_unlimited = 0
            self.camera.arm(2)
            self.camera.issue_software_trigger()

            self.live_thread = ImageAcquisitionThread(self.camera)
            self.live_thread.start()
            self.is_live = True
            return self.live_thread.get_output_queue()

    def stop_live_view(self):
        with self._lock:
            if not self.is_live or not self.live_thread:
                return

            print("[CAM] Zatrzymywanie Live View")
            self.live_thread.stop()
            self.live_thread.join()

            self.camera.disarm()
            self.is_live = False
            self.live_thread = None

    def capture_frame(self):
        with self._lock:
            if self.is_live:
                return None

            self.camera.frames_per_trigger_zero_for_unlimited = 0
            
            self.camera.image_poll_timeout_ms = int(self.camera.exposure_time_us / 1000) + 1000
            
            self.camera.arm(2)
            self.camera.issue_software_trigger()

            frame = self.camera.get_pending_frame_or_null()

            if frame is None:
                print("[CAM] Błąd: nie udalo sie pobrac klatki")
                self.camera.disarm()
                return None

            img = np.copy(frame.image_buffer)

            numpy_shaped_image = img.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels)

            self.camera.disarm()
            return numpy_shaped_image

    def save_frame(self, filename):
        frame = self.capture_frame()
        if frame is not None:
            Image.fromarray(frame).save(filename)

    def close(self):
        if self.is_live:
            self.stop_live_view()

        with self._lock:
            self.camera.dispose()
            self.sdk.dispose()