import serial
import time
from threading import Event

BAUD_RATE = 115200

class GRBLcontrol():
    def __init__(self):
        self.grbl_port_path = 'COM5'

    def remove_comment(self, string):
        if (string.find(';') == -1):
            return string
        else:
            return string[:string.index(';')]

    def remove_eol_chars(self, string):
        return string.strip()

    def send_wake_up(self, ser):
        ser.write(str.encode("\r\n\r\n"))
        time.sleep(2)
        ser.reset_input_buffer()

    def wait_for_movement_completion(self, ser, cleaned_line):
        Event().wait(1)
        if cleaned_line not in ['$X', '$$']:
            idle_counter = 0
            while True:
                ser.reset_input_buffer()
                command = str.encode('?' + '\n')
                ser.write(command)
                grbl_out = ser.readline()
                grbl_response = grbl_out.strip().decode('utf-8')

                if grbl_response != 'ok':
                    if 'Idle' in grbl_response:
                        idle_counter += 1

                if idle_counter > 10:
                    break
        return

    def stream_gcode(self, gcode_path):
        with open(gcode_path, "r") as file, serial.Serial(self.grbl_port_path, BAUD_RATE) as ser:
            self.send_wake_up(ser)

            for line in file:
                cleaned_line = self.remove_eol_chars(self.remove_comment(line))

                if cleaned_line:
                    print("Sending gcode:" + str(cleaned_line))
                    command = str.encode(line + '\n')
                    ser.write(command)

                    self.wait_for_movement_completion(ser, cleaned_line)

                    grbl_out = ser.readline()
                    print(" : ", grbl_out.strip().decode('utf-8'))

            print('End of gcode')

class Platform:
    def __init__(self):
        self.grbl = GRBLcontrol()

    def move_z_plus(self):
        self.grbl.stream_gcode('grbl_homePos.gcode')

    def move_z_minus(self):
        print("Z -")

    def adjust_lighting(self):
        pass

if __name__ == "__main__":
    platform = Platform()
    platform.move_z_plus()