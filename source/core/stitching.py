import json
import os

import numpy as np
from PIL import Image


class MosaicStitcher:
    def __init__(self, mosaic_folder_path):
        self.folder_path = mosaic_folder_path
        self.layout_file = os.path.join(self.folder_path, "mosaic_layout.json")

    def _create_feathering_mask(self, h, w):
        y, x = np.indices((h, w))
        dist_x = np.minimum(x, w - 1 - x)
        dist_y = np.minimum(y, h - 1 - y)
        mask = np.minimum(dist_x, dist_y).astype(np.float32)
        if mask.max() > 0:
            mask /= mask.max()
        return mask

    def stitch(self, output_filename="final_hypercube.tiff"):
        print(f"[STITCHER] Rozpoczynam zszywanie mozaiki z folderu: {self.folder_path}")

        if not os.path.exists(self.layout_file):
            print("[STITCHER] Blad: Nie znaleziono pliku mosaic_layout.json!")
            return False

        with open(self.layout_file, "r", encoding="utf-8") as f:
            layout_data = json.load(f)

        tiles_info = layout_data.get("tiles", [])
        if not tiles_info:
            print("[STITCHER] Blad: Brak kafelkow w pliku layoutu.")
            return False

        first_tile_path = os.path.join(self.folder_path, tiles_info[0]["filename"])
        try:
            first_img = Image.open(first_tile_path)
            tile_w, tile_h = first_img.size
            num_wavelengths = getattr(first_img, "n_frames", 1)
        except Exception as e:
            print(f"[STITCHER] Blad przy otwieraniu pierwszego kafelka: {e}")
            return False

        fov_x_mm = layout_data["fov_x"]
        fov_y_mm = layout_data["fov_y"]
        ppm_x = tile_w / fov_x_mm
        ppm_y = tile_h / fov_y_mm

        min_x_mm = min(t["relative_x"] for t in tiles_info)
        min_y_mm = min(t["relative_y"] for t in tiles_info)
        max_x_mm = max(t["relative_x"] for t in tiles_info)
        max_y_mm = max(t["relative_y"] for t in tiles_info)

        final_canvas_w = int((max_x_mm - min_x_mm) * ppm_x) + tile_w
        final_canvas_h = int((max_y_mm - min_y_mm) * ppm_y) + tile_h

        print(
            f"[STITCHER] Wyliczono plotno: {final_canvas_w} x {final_canvas_h} pikseli, "
            f"{num_wavelengths} dlugosci fal."
        )

        blend_mask = self._create_feathering_mask(tile_h, tile_w)
        final_frames_pil = []

        for frame_idx in range(num_wavelengths):
            print(f"[STITCHER] Przetwarzam kanal {frame_idx + 1}/{num_wavelengths}...")

            accumulator = np.zeros((final_canvas_h, final_canvas_w), dtype=np.float32)
            weight_sum = np.zeros((final_canvas_h, final_canvas_w), dtype=np.float32)

            for tile in tiles_info:
                tile_path = os.path.join(self.folder_path, tile["filename"])

                img = Image.open(tile_path)
                img.seek(frame_idx)
                tile_array = np.array(img).astype(np.float32)

                pixel_x = int((tile["relative_x"] - min_x_mm) * ppm_x)
                pixel_y = int((tile["relative_y"] - min_y_mm) * ppm_y)

                end_y = min(pixel_y + tile_h, final_canvas_h)
                end_x = min(pixel_x + tile_w, final_canvas_w)

                act_tile_h = end_y - pixel_y
                act_tile_w = end_x - pixel_x

                target_region = tile_array[:act_tile_h, :act_tile_w]
                mask_region = blend_mask[:act_tile_h, :act_tile_w]

                accumulator[pixel_y:end_y, pixel_x:end_x] += target_region * mask_region
                weight_sum[pixel_y:end_y, pixel_x:end_x] += mask_region

            weight_sum[weight_sum == 0] = 1.0
            blended_canvas = accumulator / weight_sum
            blended_canvas = np.clip(blended_canvas, 0, 65535).astype(np.uint16)
            final_frames_pil.append(Image.fromarray(blended_canvas))

        output_path = os.path.join(self.folder_path, output_filename)
        print(f"[STITCHER] Zapisuje do wielostronicowego TIFF: {output_path}")

        try:
            final_frames_pil[0].save(
                output_path,
                save_all=True,
                append_images=final_frames_pil[1:]
            )
            print("[STITCHER] Zszywanie zakonczone sukcesem!")
            return True
        except Exception as e:
            print(f"[STITCHER] Blad podczas zapisu finalnego tiffa: {e}")
            return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    else:
        test_folder = input("Podaj pelna sciezke do folderu z kafelkami: ")
    stitcher = MosaicStitcher(test_folder)
    stitcher.stitch()
