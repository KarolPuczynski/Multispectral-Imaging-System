from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import QTimer, Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
from PIL import ImageQt
import queue
import numpy as np


class LiveViewWidget(QLabel):
    """ A custom QLabel widget that displays a live video feed from the camera."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: black;")
        self.setMinimumSize(480, 360)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self.image_queue = None
        self._is_running = False

        self._frame_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_loop)

    def sizeHint(self):
        return QSize(800, 600)

    def minimumSizeHint(self):
        return QSize(480, 360)

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
            
            # Calculate mean of full image (e.g. 4096x3000) for calibration
            img_array = np.array(image)
            h, w = img_array.shape[:2]
            mean_val_8bit = np.mean(img_array)

            # Symulacja wartosci 10-bitowej dla spojnosci z zapisanymi plikami TIFF
            mean_val_10bit = mean_val_8bit * 4

            # Obliczanie histogramu dla calej klatki (8-bit)
            hist, _ = np.histogram(img_array, bins=256, range=(0, 256))

            # Precyzyjne dane w konsoli (wyswietlane co 10 klatek)
            self._frame_count += 1
            if self._frame_count % 10 == 0:
                peak_bin = np.argmax(hist)
                img_min = img_array.min()
                img_max = img_array.max()
                print(f"[LIVE] Średnia (10-bit): {mean_val_10bit:.4f} | Min: {img_min} | Max: {img_max} | Dominanta (Peak): {peak_bin}")

            qim = ImageQt.ImageQt(image)
            pixmap = QPixmap.fromImage(qim)
            
            # Draw the mean value on the image
            painter = QPainter(pixmap)

            # Ostrzezenie o przeswietleniu (powyzej 1000 dla 10-bit)
            is_overexposed = mean_val_10bit > 1000
            box_color = QColor(224, 85, 85) if is_overexposed else QColor(45, 202, 165)

            font = painter.font()
            font.setPointSize(28)
            font.setBold(True)
            painter.setFont(font)
            
            warning_str = " - ZBYT JASNE!" if is_overexposed else ""
            
            # Draw text with a slight shadow/background for visibility
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.drawText(12, 42, f"Srednia obrazu: ~{mean_val_10bit:.1f} (10-bit){warning_str}")
            painter.setPen(QPen(box_color, 2))
            painter.drawText(10, 40, f"Srednia obrazu: ~{mean_val_10bit:.1f} (10-bit){warning_str}")

            # Rysowanie histogramu w prawym dolnym rogu
            hist_w = 256
            hist_h = 100
            hist_x = w - hist_w - 20
            hist_y = h - hist_h - 20
            
            painter.fillRect(hist_x, hist_y, hist_w, hist_h, QColor(0, 0, 0, 150))
            
            max_val = hist.max()
            if max_val > 0:
                painter.setPen(QPen(QColor(200, 200, 200), 1))
                for i in range(256):
                    val = int((hist[i] / max_val) * hist_h)
                    if val > 0:
                        painter.drawLine(hist_x + i, hist_y + hist_h, hist_x + i, hist_y + hist_h - val)
            
            painter.setPen(QPen(QColor(45, 202, 165), 1))
            painter.drawRect(hist_x, hist_y, hist_w, hist_h)

            painter.end()

            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)

        except queue.Empty:
            pass
        except Exception as e:
            print(f"[INFO] Błąd wyświetlania (LiveView): {e}")
