from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PIL import ImageQt
import queue
class LiveViewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: black;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.image_queue = None
        self._is_running = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_loop)

    def start_live_view(self, new_image_queue):
        self.image_queue = new_image_queue
        self._is_running = True
        self.timer.start(30)  # okolo 33 FPS

    def stop_live_view(self):
        self._is_running = False
        self.timer.stop()
        self.image_queue = None
        self.clear()
        self.setText("Live View Stopped")

    def _update_loop(self):
        if not self._is_running or self.image_queue is None:
            return

        try:
            image = self.image_queue.get_nowait()

            qim = ImageQt.ImageQt(image)
            pixmap = QPixmap.fromImage(qim)
            
            scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(scaled_pixmap)

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Błąd wyświetlania: {e}")