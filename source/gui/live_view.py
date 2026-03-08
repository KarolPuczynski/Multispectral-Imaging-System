import tkinter as tk
from PIL import Image, ImageTk
import queue


class LiveViewCanvas(tk.Canvas):
    def __init__(self, parent):
        tk.Canvas.__init__(self, parent, bg="black")
        self.pack(fill="both", expand=True)

        self.image_queue = None
        self._image_width = 0
        self._image_height = 0
        self._is_running = False
        self._image = None


    def start_live_view(self, new_image_queue):
        self.image_queue = new_image_queue
        self._is_running = True
        self._update_loop()

    def stop_live_view(self):
        self._is_running = False
        self.image_queue = None
        self.delete("all")
    def _update_loop(self):
        if not self._is_running or self.image_queue is None:
            return

        try:
            image = self.image_queue.get_nowait()

            self._image = ImageTk.PhotoImage(master=self, image=image)

            if (self._image.width() != self._image_width) or (self._image.height() != self._image_height):
                self._image_width = self._image.width()
                self._image_height = self._image.height()
                self.config(width=self._image_width, height=self._image_height)

            self.create_image(0, 0, image=self._image, anchor='nw')

        except queue.Empty:
            pass
        except Exception as e:
            print(f"Błąd wyświetlania: {e}")

        self.after(20, self._update_loop)