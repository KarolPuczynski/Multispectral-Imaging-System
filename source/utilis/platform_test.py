import serial
import time


BAUD_RATE = 115200
PORT = "COM5"


class GRBLcontrol:

    def __init__(self, port=PORT, baud=BAUD_RATE):
        self.port = port
        self.baud = baud
        self.ser = None

    # -----------------------------
    # CONNECT / DISCONNECT
    # -----------------------------
    def connect(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=1)
        self.wake_up()
        print("Connected to GRBL")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected")

    # -----------------------------
    # WAKE UP GRBL
    # -----------------------------
    def wake_up(self):
        self.ser.write(b"\r\n\r\n")
        time.sleep(2)
        self.ser.reset_input_buffer()

    # -----------------------------
    # READ UNTIL OK / ERROR
    # -----------------------------
    def read_until_ok(self):
        while True:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            print("<<", line)

            if line == "ok" or line.startswith("error:"):
                return line

    # -----------------------------
    # WAIT FOR IDLE (for movements)
    # -----------------------------
    def wait_for_idle(self):
        while True:
            self.ser.write(b"?\n")
            status = self.ser.readline().decode("utf-8", errors="ignore").strip()

            if status:
                # przykładowy status:
                # <Idle|MPos:0.000,0.000,0.000|FS:0,0>
                if "Idle" in status:
                    return

            time.sleep(0.1)

    # -----------------------------
    # SEND COMMAND
    # -----------------------------
    def send(self, command, wait_idle=False):
        print(">>", command)
        self.ser.write((command + "\n").encode())

        response = self.read_until_ok()

        if wait_idle and not response.startswith("error"):
            self.wait_for_idle()

    # -----------------------------
    # BASIC MOVEMENTS
    # -----------------------------
    def unlock(self):
        self.send("$X")

    def relative_mode(self):
        self.send("G91")

    def absolute_mode(self):
        self.send("G90")

    def move_x(self, distance):
        self.relative_mode()
        self.send(f"G0 X{distance}", wait_idle=True)
        self.absolute_mode()

    def move_y(self, distance):
        self.relative_mode()
        self.send(f"G0 Y{distance}", wait_idle=True)
        self.absolute_mode()

    def move_z(self, distance):
        self.relative_mode()
        self.send(f"G0 Z{distance}", wait_idle=True)
        self.absolute_mode()

    # -----------------------------
    # STREAM FILE
    # -----------------------------
    def stream_file(self, filepath):
        with open(filepath, "r") as file:
            for line in file:
                cleaned = line.strip()

                if cleaned and not cleaned.startswith(";"):
                    self.send(cleaned, wait_idle=True)

        print("Finished streaming file")


# ======================================================
# MAIN
# ======================================================

if __name__ == "__main__":

    grbl = GRBLcontrol()
    grbl.connect()

    try:
        grbl.unlock()

        # Test ruchu osi Z
        grbl.move_x(-0.3)  #z

    finally:
        grbl.disconnect()