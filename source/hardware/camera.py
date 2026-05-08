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
from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
from thorlabs_tsi_sdk.tl_mono_to_color_processor import MonoToColorProcessorSDK

DEFAULT_GAIN = 1

class ImageAcquisitionThread(threading.Thread):
    def __init__(self, camera):
        super(ImageAcquisitionThread, self).__init__()
        self._camera = camera
        self._previous_timestamp = 0

        # setup color processing
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            self._is_color = False
        else:
            self._mono_to_color_sdk = MonoToColorProcessorSDK()
            self._image_width = self._camera.image_width_pixels
            self._image_height = self._camera.image_height_pixels
            self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
                SENSOR_TYPE.BAYER,
                self._camera.color_filter_array_phase,
                self._camera.get_color_correction_matrix(),
                self._camera.get_default_white_balance_matrix(),
                self._camera.bit_depth
            )
            self._is_color = True

        self._bit_depth = camera.bit_depth
        self._camera.image_poll_timeout_ms = 0
        self._image_queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

    def get_output_queue(self):
        return self._image_queue

    def stop(self):
        self._stop_event.set()

    def _get_color_image(self, frame):
        width = frame.image_buffer.shape[1]
        height = frame.image_buffer.shape[0]
        if (width != self._image_width) or (height != self._image_height):
            self._image_width = width
            self._image_height = height

        color_image_data = self._mono_to_color_processor.transform_to_24(
            frame.image_buffer, self._image_width, self._image_height
        )
        color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
        return Image.fromarray(color_image_data, mode='RGB')

    def _get_image(self, frame):
        scaled_image = (frame.image_buffer >> (self._bit_depth - 8)).astype(np.uint8)
        return Image.fromarray(scaled_image)

    def run(self):
        while not self._stop_event.is_set():
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    if self._is_color:
                        pil_image = self._get_color_image(frame)
                    else:
                        pil_image = self._get_image(frame)
                    self._image_queue.put_nowait(pil_image)
            except queue.Full:
                pass
            except Exception as error:
                print(f"[CAM] Error in acquisition thread: {error}")
                break

        if self._is_color:
            self._mono_to_color_processor.dispose()
            self._mono_to_color_sdk.dispose()
        print("[CAM] Image acquisition thread stopped.")


class ThorlabsCamera:
    def __init__(self, exposure_us=10000):
        self.sdk = TLCameraSDK()
        cameras = self.sdk.discover_available_cameras()
        if not cameras:
            raise RuntimeError("[CAM] Brak podłączonych kamer Thorlabs.")

        self.camera = self.sdk.open_camera(cameras[0])
        self.camera.exposure_time_us = exposure_us

        # Ustawienia domyślne gain
        if hasattr(self.camera, "gain"):
            self.camera.gain = DEFAULT_GAIN
        elif hasattr(self.camera, "analog_gain"):
            self.camera.analog_gain = DEFAULT_GAIN

        # Zmienne do Live View
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