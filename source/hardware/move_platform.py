import os
from core.grbl_handling import GrblClient

class Platform:
    def __init__(self):
        self.grbl = GrblClient()

        # zakres roboczy platformy w mm
        self.platform_min = (0.0, 0.0, 0.0) # minimalne położenie (x, y, z)
        self.platform_max = (200.0, 200.0, 100.0) # maksymalne położenie (x, y, z)

        self.x_state = 0.0
        self.y_state = 0.0
        self.z_state = 0.0

    def connect(self):
        self.grbl.connect()

    def homing(self):
        self.grbl.send_line_async('$H')
        self.x_state = 0.0
        self.y_state = 0.0
        self.z_state = 0.0

    def unlock(self):
        self.grbl.send_line_async('$X')

    def grblsetup(self):
        gcode_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grblsetup.gcode')
        self.grbl.stream_gcode(gcode_path)

    def move_single_axis(self, gcode):
        self.grbl.send_line_async(gcode)

    def validate_platform_movement(self, axis, distance):
        if axis == 'X':
            new_x = self.x_state + distance
            if new_x >= self.platform_min[0] and new_x <= self.platform_max[0]:
                self.x_state = new_x
                return True
            else:
                return False
        elif axis == 'Y':
            new_y = self.y_state + distance
            if new_y >= self.platform_min[1] and new_y <= self.platform_max[1]:
                self.y_state = new_y
                return True
            else:
                return False
        elif axis == 'Z':
            new_z = self.z_state + distance
            if new_z >= self.platform_min[2] and new_z <= self.platform_max[2]:
                self.z_state = new_z
                return True
            else:
                return False
        else:
            return False            

    def adjust_lighting(self):
        pass

if __name__ == "__main__":
    platform = Platform()
    platform.grblsetup()
    #platform.move_single_axis(gcode='G91 X1')
    