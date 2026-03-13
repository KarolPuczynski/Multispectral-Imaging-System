import serial
import time

class LedController:
    def __init__(self, port="COM6", baudrate=9600):
        # Domyślny port COM3 - upewnij się, że w Menedżerze Urządzeń 
        # Twoje drugie Arduino ma taki numer, lub zmień go tutaj.
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False

    def connect(self):
        if self.connected:
            print("[PWM] Już połączono.")
            return

        try:
            print(f"[PWM] Łączenie z sterownikiem światła na porcie {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            # Po otwarciu portu Arduino zwykle się resetuje, dajemy mu chwilę
            time.sleep(2.0)
            self.connected = True
            print(f"[PWM] Połączono pomyślnie.")
        except Exception as e:
            print(f"[PWM] Błąd połączenia: {e}")
            self.connected = False

    def set_pwm(self, value):
        if not self.connected or not self.ser:
            return

        try:
            # Wysyłamy wartość jako tekst zakończony nową linią (np. "128\n")
            # Kod na Arduino powinien to odebrać (Serial.parseInt() lub podobne)
            command = f"{int(value)}\n"
            self.ser.write(command.encode('ascii'))
        except Exception as e:
            print(f"[PWM] Błąd wysyłania komendy: {e}")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.connected = False
            print("[PWM] Rozłączono.")
