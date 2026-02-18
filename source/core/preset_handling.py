import json
import os

class PresetManager:
    def __init__(self, json_path):
        self.json_path = json_path
        self.presets = {}
        self.load_presets()

    def load_presets(self):
        if not os.path.exists(self.json_path):
            print(f"Plik {self.json_path} nie istnieje.")
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            self.presets = json.load(f)

    def get_preset_names(self):
        return list(self.presets.keys())

    def get_preset_data(self, name):
        return self.presets.get(name)

    def save_new_preset(self, name, data_dict):
        self.presets[name] = data_dict

        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.presets, f, indent=4)
        print(f"[PRESET] Zapisano preset '{name}'")