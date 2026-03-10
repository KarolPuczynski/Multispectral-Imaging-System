import os
from core.grbl_handling import GrblClient

class Platform:
    def __init__(self):
        self.grbl = GrblClient()
        self.grbl.connect()
        # tu se dodamy aktualne pozycje osi, zeby potem nie wychodzic poza zakres
        self.x_state = 0.0
        self.y_state = 0.0

    def homing(self):
        self.grbl.send_line_async('$H')

    def unlock(self):
        self.grbl.send_line_async('$X')

    def grblsetup(self):
        gcode_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grblsetup.gcode')
        self.grbl.stream_gcode(gcode_path)

    def move_single_axis(self, gcode):
        # trzeba tu bedzie napisac warunki zeby nie wykroczyc poza zasieg platformy
        # i dopiero potem przeslac kod
        self.grbl.send_line_async(gcode)

    def adjust_lighting(self):
        pass

if __name__ == "__main__":
    platform = Platform()
    platform.grblsetup()
    #platform.move_single_axis(gcode='G91 X1')
    