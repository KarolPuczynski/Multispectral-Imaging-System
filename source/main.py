import tkinter as tk
from gui.application import App

if __name__ == "__main__":
    root = tk.Tk()

    # Maximize the window to fit the screen
    root.state('zoomed')

    app = App(root)
    root.mainloop()