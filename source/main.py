import tkinter as tk
from gui.application import App

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900

if __name__ == "__main__":
    root = tk.Tk()

    root.geometry(f'{WINDOW_WIDTH}x{WINDOW_HEIGHT}')

    app = App(root)
    root.mainloop()