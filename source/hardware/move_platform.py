import math
import os
import time

from hardware.grbl_handling import GrblClient


class Platform:
    def __init__(self):
        self.grbl = GrblClient()
        self.is_ready = False

        # Zakres roboczy platformy w mm: (x, y, z).
        self.platform_min = (0.0, 0.0, 0.0)
        self.platform_max = (80.0, 45.0, 100.0)

        self.x_state = 0.0
        self.y_state = 0.0
        self.z_state = 0.0

        # Pozycja XY, w ktorej probka jest centralnie pod kamera.
        self.platform_center = (40.0, 22.5)

    def connect(self):
        self.grbl.connect()

    def homing(self):
        self.grbl.send_line_async('$H')
        self.x_state = 0.0
        self.y_state = 0.0
        self.z_state = 0.0
        self.is_ready = True

    def unlock(self):
        self.grbl.send_line_async('$X')
        self.is_ready = True

    def grblsetup(self):
        gcode_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grbl_setup.gcode')
        self.grbl.stream_gcode(gcode_path)

    def move_single_axis(self, gcode):
        self.grbl.send_line_async(gcode)

    def validate_and_move(self, axis, step, direction):
        distance = step * direction

        if axis == 'X':
            new_x = self.x_state + distance
            if self.platform_min[0] <= new_x <= self.platform_max[0]:
                self.x_state = new_x
                self.move_single_axis(f'G91 {axis}{distance:.3f} F500')
                return True
            return False

        if axis == 'Y':
            new_y = self.y_state + distance
            if self.platform_min[1] <= new_y <= self.platform_max[1]:
                self.y_state = new_y
                self.move_single_axis(f'G91 {axis}{distance:.3f} F500')
                return True
            return False

        if axis == 'Z':
            distance = distance / 1
            new_z = self.z_state + distance
            if self.platform_min[2] <= new_z <= self.platform_max[2]:
                self.z_state = new_z
                self.move_single_axis(f'G91 {axis}{distance:.3f} F500')
                return True
            return False

        return False

    def move_to_center(self):
        x_distance_to_center = self.platform_center[0] - self.x_state
        y_distance_to_center = self.platform_center[1] - self.y_state

        if x_distance_to_center != 0 or y_distance_to_center != 0:
            self.move_single_axis(f'G91 X{x_distance_to_center:.3f} Y{y_distance_to_center:.3f} F500')
            self.x_state = self.platform_center[0]
            self.y_state = self.platform_center[1]

    def move_to_position_blocking(self, target_x, target_y, feedrate=500):
        if target_x < self.platform_min[0] or target_x > self.platform_max[0] or \
                target_y < self.platform_min[1] or target_y > self.platform_max[1]:
            print(f"[BLAD] Cel X:{target_x:.2f}, Y:{target_y:.2f} poza zakresem! RUCH ZABLOKOWANY.")
            return False

        dx = target_x - self.x_state
        dy = target_y - self.y_state
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return True

        response = self.grbl.send_line_blocking(f'G91 G1 X{dx:.3f} Y{dy:.3f} F{feedrate}')
        if response.startswith('error'):
            print(f"[GRBL] Blad ruchu XY: {response}")
            return False

        self.x_state = target_x
        self.y_state = target_y

        move_time_seconds = distance / (feedrate / 60.0)
        time.sleep(move_time_seconds + 1.5)
        return True


if __name__ == "__main__":
    platform = Platform()
    platform.grblsetup()
