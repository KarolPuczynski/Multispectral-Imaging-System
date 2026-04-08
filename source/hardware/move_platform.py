import os
import math
import time
from hardware.grbl_handling import GrblClient

class Platform:
    def __init__(self):
        self.grbl = GrblClient()
        self.is_ready = False

        # zakres roboczy platformy w mm
        self.platform_min = (0.0, 0.0, 0.0) # minimalne położenie (x, y, z)
        self.platform_max = (65.0, 60.0, 100.0) # maksymalne położenie (x, y, z)

        # polozenie wszystkich osi platformy w mm
        self.x_state = 0.0
        self.y_state = 0.0
        self.z_state = 0.0

        # pozycja xy platformy (w mm), ktora podjezdza centralnie pod kamerke
        # TODO trzeba dokladnei to wymierzyc
        self.platform_center = (30.0, 30.0)

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
        gcode_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grblsetup.gcode')
        self.grbl.stream_gcode(gcode_path)

    def move_single_axis(self, gcode):
        self.grbl.send_line_async(gcode)

    def validate_and_move(self, axis, step, direction):

        distance = step * direction

        if axis == 'X':
            new_x = self.x_state + distance
            
            if new_x >= self.platform_min[0] and new_x <= self.platform_max[0]:
                self.x_state = new_x
                self.move_single_axis(f'G91 {axis}{distance} F500')
                return True
            else:
                return False
            
        elif axis == 'Y':
            new_y = self.y_state + distance

            if new_y >= self.platform_min[1] and new_y <= self.platform_max[1]:
                self.y_state = new_y
                self.move_single_axis(f'G91 {axis}{distance} F500')
                return True
            else:
                return False
            
        elif axis == 'Z':
            distance = distance / 1 # wspolczynnik skalowanosci os Z (XD)
            new_z = self.z_state + distance
            
            if new_z >= self.platform_min[2] and new_z <= self.platform_max[2]:
                self.z_state = new_z
                self.move_single_axis(f'G91 {axis}{distance} F500')
                return True
            else:
                return False
        else:
            return False            

    def move_to_center(self):
        x_distance_to_center = self.platform_center[0] - self.x_state
        y_distance_to_center = self.platform_center[1] - self.y_state

        if x_distance_to_center != 0 or y_distance_to_center != 0:
            self.move_single_axis(f'G91 X{x_distance_to_center} Y{y_distance_to_center} F500')
            self.x_state = self.platform_center[0]
            self.y_state = self.platform_center[1]

    def move_to_position_blocking(self, target_x, target_y):
        # Obliczanie fizycznego dystansu do pokonania
        dx = target_x - self.x_state
        dy = target_y - self.y_state
        distance = math.sqrt(dx ** 2 + dy ** 2)

        if distance == 0:
            return True

        # Przejście w tryb absolutny (G90), wysłanie ruchu i powrót do relatywnego (G91)
        feedrate = 500
        self.move_single_axis(f'G90')
        self.move_single_axis(f'G1 X{target_x} Y{target_y} F{feedrate}')
        self.move_single_axis(f'G91')

        # Aktualizacja wewnętrznego stanu w Pythonie
        self.x_state = target_x
        self.y_state = target_y

        # Obliczanie czasu i oczekiwanie na ustabilizowanie
        # Prędkość to 500 mm/min = ok. 8.33 mm/sek
        move_time_seconds = distance / (feedrate / 60.0)

        # 0.5s marginesu na wytracenie pędu i wibracji stolika
        time.sleep(move_time_seconds + 0.5)

        return True
        

if __name__ == "__main__":
    platform = Platform()
    platform.grblsetup()
    #platform.move_single_axis(gcode='G91 X1')
    