class LedController:
    def __init__(self, grbl_client, input_max=255, spindle_max=1000):
        self.grbl = grbl_client
        self.input_max = input_max
        self.spindle_max = spindle_max
        self.connected = False

    def connect(self):
        self.connected = bool(self.grbl.ser and self.grbl.ser.is_open)
        if self.connected:
            print("[PWM] Sterowanie oswietleniem przez GRBL aktywne.")
        else:
            print("[PWM] Brak polaczenia GRBL. PWM niedostepne.")

    def set_pwm(self, value):
        if not self.grbl.ser or not self.grbl.ser.is_open:
            self.connected = False
            return

        try:
            value = max(0, min(self.input_max, int(value)))
            spindle_value = round((value / self.input_max) * self.spindle_max)

            if spindle_value <= 0:
                self.grbl.send_line_async("M5")
            else:
                self.grbl.send_line_async(f"M3 S{spindle_value}")

            self.connected = True
        except Exception as e:
            print(f"[PWM] Blad wysylania komendy GRBL PWM: {e}")

    def close(self):
        self.set_pwm(0)
        self.connected = False
        print("[PWM] Wylaczono oswietlenie.")
