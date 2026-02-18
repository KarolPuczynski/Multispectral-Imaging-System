import KURIOS_COMMAND_LIB as kurios

class KuriosController:
    def __init__(self):
        self.kur = kurios.Kurios()
        devices = self.kur.list_devices()
        if not devices:
            raise RuntimeError("Nie znaleziono urządzeń KURIOS.")
        self.serial = devices[0][0]
        if self.kur.open(self.serial, 115200, 1) >= 0:
            print(f"Połączono z filtrem KURIOS ({self.serial})")
        else:
            raise RuntimeError("Nie udało się otworzyć połączenia z KURIOS.")

    def set_wavelength(self, wl):
        self.kur.SetWavelength(int(wl))
        print(f"Ustawiono długość fali: {wl} nm")

    def set_bandwidth(self, mode):
        self.kur.SetBandwidthMode(int(mode))
        print(f"Tryb pasma ustawiony: {mode}")

    def get_wavelength(self):
        val = [0]
        self.kur.GetWavelength(val)
        return val[0]

    def close(self):
        self.kur.close()
        print("Zamknięto połączenie z KURIOS.")
