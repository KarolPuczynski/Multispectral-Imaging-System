import queue
import threading
import time

import serial


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
            if self.is_connected():
                return True
            self.disconnect()

        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        except (serial.SerialException, OSError) as e:
            print(f"[GRBL] Blad otwarcia portu {self.port}: {e}")
            self.ser = None
            return False

        time.sleep(2.0)

        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            self.ser.write(b"\r\n\r\n")
            self.ser.flush()
            time.sleep(0.2)
            self.ser.reset_input_buffer()
            print(f"[GRBL] Polaczono z GRBL na porcie {self.port}")
            return True
        except (serial.SerialException, OSError) as e:
            print(f"[GRBL] Blad inicjalizacji portu {self.port}: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except (serial.SerialException, OSError):
                pass
        self.ser = None
        print("[GRBL] Rozlaczono z GRBL")

    def force_stop(self):
        if not self.ser or not self.ser.is_open:
            return

        try:
            self._clear_command_queue()

            lock_acquired = self.lock.acquire(blocking=False)
            try:
                # GRBL realtime: feed hold, then soft reset. Soft reset also stops spindle/laser output.
                self.ser.write(b"!\x18")
                self.ser.flush()
                time.sleep(0.1)
                self.ser.reset_input_buffer()
            finally:
                if lock_acquired:
                    self.lock.release()
        except (serial.SerialException, OSError) as e:
            print(f"[GRBL] Blad awaryjnego zatrzymania: {e}")
            self.disconnect()

    def _clear_command_queue(self):
        while True:
            try:
                self.command_queue.get_nowait()
                self.command_queue.task_done()
            except queue.Empty:
                break

    def is_connected(self) -> bool:
        if not self.ser or not self.ser.is_open:
            return False

        try:
            with self.lock:
                self.ser.write(b"?")
                self.ser.flush()

                deadline = time.time() + 0.5
                while time.time() < deadline:
                    raw = self.ser.readline()
                    if not raw:
                        continue

                    status = raw.decode("ascii", errors="ignore").strip()
                    if status.startswith("<") and status.endswith(">"):
                        return True

            print("[GRBL] Brak odpowiedzi statusowej z GRBL.")
            return False
        except (serial.SerialException, OSError):
            print("[GRBL] Utracono polaczenie z GRBL.")
            self.disconnect()
            return False

    def _worker_loop(self):
        while True:
            try:
                command = self.command_queue.get()
                self.send_line_blocking(command)
                self.command_queue.task_done()
            except Exception as e:
                print(f"[GRBL] Blad w watku GRBL: {e}")

    def send_line_async(self, line: str):
        self.command_queue.put(line)

    def send_line_blocking(self, line: str, wait_ok=True, timeout: float = 3.0) -> str:
        if not self.ser or not self.ser.is_open:
            print("[GRBL] Blad: Brak polaczenia. Komenda zignorowana.")
            return ""

        cmd = line.strip()
        if not cmd:
            return ""

        with self.lock:
            try:
                self.ser.write((cmd + "\n").encode("ascii", errors="ignore"))
                self.ser.flush()
            except (serial.SerialException, OSError) as e:
                print(f"[GRBL] Blad wysylania komendy. Utracono polaczenie: {e}")
                self.disconnect()
                return ""

            if not wait_ok:
                return ""

            lines = []
            deadline = time.time() + timeout

            while time.time() < deadline:
                try:
                    raw = self.ser.readline()
                except (serial.SerialException, OSError) as e:
                    print(f"[GRBL] Blad odczytu. Utracono polaczenie: {e}")
                    self.disconnect()
                    return "\n".join(lines)

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
            raise RuntimeError("Nie polaczono z Arduino (COM).")
        with self.lock:
            try:
                self.ser.write(ch)
                self.ser.flush()
            except (serial.SerialException, OSError):
                self.disconnect()
                raise

    def stream_gcode(self, gcode_path):
        print(f"[GRBL] Streaming pliku G-code: {gcode_path}")
        try:
            with open(gcode_path, "r") as file:
                for line in file:
                    if ";" in line:
                        line = line[:line.index(";")]
                    cleaned = line.strip()

                    if cleaned:
                        print(f"[GRBL] Wysylanie: {cleaned}")
                        response = self.send_line_blocking(cleaned)
                        print(f"[GRBL] Odpowiedz: {response}")
            print("[GRBL] Zakonczono wysylanie pliku G-code")
        except FileNotFoundError:
            print(f"[GRBL] Blad: Nie znaleziono pliku {gcode_path}")
