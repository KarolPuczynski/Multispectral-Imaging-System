import threading
import time
import serial
import queue

class GrblClient:
    def __init__(self, port="COM7", baud=115200, timeout=1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self.lock = threading.Lock()
        
        self.command_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def connect(self):
        if self.ser and self.ser.is_open:
            return

        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        except serial.SerialException as e:
            print(f"Błąd otwarcia portu {self.port}: {e}")
            return

        time.sleep(2.0)

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        self.ser.write(b"\r\n\r\n")
        self.ser.flush()
        time.sleep(0.2)
        self.ser.reset_input_buffer()
        print(f"Połączono z GRBL na porcie {self.port}")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None
        print("Rozłączono z GRBL")

    def _worker_loop(self):
        while True:
            try:
                command = self.command_queue.get()
                self.send_line_blocking(command)
                self.command_queue.task_done()
            except Exception as e:
                print(f"Błąd w wątku GRBL: {e}")

    def send_line_async(self, line: str):
        self.command_queue.put(line)

    def send_line_blocking(self, line: str, wait_ok=True) -> str:
        if not self.ser or not self.ser.is_open:
            print("[GRBL] Błąd: Brak połączenia.")
            return ""

        cmd = line.strip()
        if not cmd:
            return ""

        with self.lock:
            self.ser.write((cmd + "\n").encode("ascii", errors="ignore"))
            self.ser.flush()

            if not wait_ok:
                return ""

            lines = []
            deadline = time.time() + 3.0

            while time.time() < deadline:
                raw = self.ser.readline()
                if not raw:
                    continue

                s = raw.decode("ascii", errors="ignore").strip()
                if not s:
                    continue

                lines.append(s)

                if s == "ok" or s.startswith("error"):
                    break

            return "\n".join(lines)

    def realtime(self, ch: bytes):
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Nie połączono z Arduino (COM).")
        with self.lock:
            self.ser.write(ch)
            self.ser.flush()

    def stream_gcode(self, gcode_path):
        print(f"Streaming pliku G-code: {gcode_path}")
        try:
            with open(gcode_path, "r") as file:
                for line in file:
                    if ';' in line:
                        line = line[:line.index(';')]
                    cleaned = line.strip()

                    if cleaned:
                        print(f"Wysyłanie: {cleaned}")
                        response = self.send_line_blocking(cleaned)
                        print(f"GRBL odp: {response}")
            print("Zakończono wysyłanie pliku G-code")
        except FileNotFoundError:
            print(f"Błąd: Nie znaleziono pliku {gcode_path}")