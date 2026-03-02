from grbl_handling import GRBLcontrol


class Platform:
    def __init__(self):
        self.grbl = GRBLcontrol()

    def homing(self):
        self.grbl.stream_gcode('$H')

    def move_single_axis(self, gcode):
        # trzeba tu bedzie napisac warunki zeby nie wykroczyc poza zasieg platformy
        # i dopiero potem przeslac kod
        self.grbl.stream_gcode(gcode)

    def adjust_lighting(self):
        pass

if __name__ == "__main__":
    platform = Platform()
    platform.move_single_axis(gcode='G91 X10')