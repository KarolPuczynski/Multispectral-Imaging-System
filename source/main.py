import sys
from PyQt6.QtWidgets import QApplication
from gui.application import App

if __name__ == "__main__":
    """ Main entry point of the application. Initializes the Qt application and launches the main window. """
    qt_app = QApplication(sys.argv)

    window = App()
    window.showMaximized()
    sys.exit(qt_app.exec())