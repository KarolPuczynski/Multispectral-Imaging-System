import tkinter as tk
from gui.application import App

if __name__ == "__main__":
    root = tk.Tk()

    root.geometry("1200x900")

    app = App(root)

    root.mainloop()