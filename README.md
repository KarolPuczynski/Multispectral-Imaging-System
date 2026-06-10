# Multispectral Imaging System

Software for managing an automated multispectral image acquisition system. The project enables the integration and control of imaging hardware (Thorlabs Camera, Kurios tunable filter) with a motorized 3-axis platform. This allows for automated spectral data collection, sample mapping, and increasing the depth of field.

## Table of Contents
1. [Main Features](#main-features)
2. [Hardware Components](#hardware-components)
3. [Project Structure](#project-structure)
4. [Installation and Running](#installation-and-running)
5. [Download Installer](#download-installer)
6. [How to Use the Project](#how-to-use-the-project)
7. [Authors](#authors)

## Main Features

- **Multispectral Scan**: Automated capturing of an image series in a specified wavelength range (e.g., 450 nm to 700 nm) with automatic exposure adjustment. Results are saved in a multi-page `.tiff` format (Hypercube).
- **Focus Stacking**: The program takes pictures of a sample at various Z-axis heights and then uses Laplacian pyramids to merge them into a single, fully sharp image.
- **Mapping & Stitching**: Generating a scanning path in X and Y axes based on the FOV and sample size. After acquisition, the program automatically stitches individual tiles to create a mosaic.
- **Preset Management**: Ability to configure and save custom scanning parameters and objective lens properties (e.g., FOV, default overlap).
- **Motorized Positioning**: Full control over the platform in 3 axes using GRBL.
- **LED Lighting**: Built-in slider for smooth lighting regulation on the microcontroller using a PWM signal.

## Hardware Components

The physical setup of the multispectral imaging platform consists of the following elements:

- **Camera**: Thorlabs CS126MU.
- **Filter**: KURIOS Tunable Filter (for wavelength tuning).
- **Microcontroller**: Arduino Uno R3 combined with a CNC Shield v3 for GRBL motor control.
- **Stepper Motors**:
  - 2x NEMA 17 stepper motors for the Z-axis.
  - 2x NEMA 17 mini stepper motors for the X and Y axes.
- **Illumination**: High-power LED regulated by a PWM module, controlled directly from the CNC Shield v3.
- **Power Supply**: AC/DC power supply unit coupled with a step-down voltage converter on the CNC Shield v3.

## Project Structure
```text
Multispectral-Imaging-System/
├── source/
│   ├── core/
│   │   ├── acquisition.py       # Orchestrates hardware for scanning and capturing images
│   │   ├── focus_stacker.py     # focus stacker implementation
│   │   ├── preset_handling.py   # Manages saving/loading JSON-based user presets
│   │   └── stitching.py         # Blends and stitches individual tiles into a full mosaic
│   ├── gui/
│   │   ├── advanced_mode.py     # Advanced settings dialog window
│   │   ├── application.py       # Main PyQt6 application window and UI logic
│   │   └── live_view.py         # Real-time camera preview widget
│   ├── hardware/
│   │   ├── camera.py            # Wrapper for Thorlabs TSI SDK camera control
│   │   ├── filter.py            # Wrapper for Kurios tunable filter commands
│   │   ├── grbl_handling.py     # Serial communication with GRBL platform
│   │   ├── led_controller.py    # PWM LED illumination control
│   │   └── platform.py          # Platform movement and coordinate tracking
│   ├── data/                    # JSON data (exposure times, presets, lens definitions)
│   └── utilis/
│       └── dll_loader.py        # Configures system paths to load required device DLLs
└── dlls/                        # Thorlabs TSI SDK and specific hardware binaries
```

## Installation and Running

### Prerequisites
- Python 3.x installed.
- Windows OS (due to support for Thorlabs TSI SDK .dll libraries).
- **Thorlabs Scientific Imaging SDK** installed on your system. You will need the Python wrapper wheel (`thorlabs_tsi_sdk-*.whl`) provided by Thorlabs to interact with the camera.
- Connected and powered-on external devices (Camera, Kurios, Platform connected to a COM port).

### Step-by-Step

1. Clone the repository to your local drive:
   ```bash
   git clone https://github.com/KarolPuczynski/Multispectral-Imaging-System.git
   ```
2. Navigate to the project folder and create a virtual environment:
   ```bash
   cd Multispectral-Imaging-System
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install required project dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Locate the file provided by Thorlabs software installation and install it manually (adjust the path if needed):
   ```bash
   pip install "C:\Program Files\Thorlabs\Scientific Imaging\Scientific Camera Support\Scientific Camera Interfaces\SDK\Python Toolkit\thorlabs_tsi_camera_python_sdk_package.zip"
   ```

5. Run the main program:
   ```bash
   python source/main.py
   ```

## Download Installer

If you don't want to install Python and run the project from source, you can download the compiled Windows installer here:

**https://drive.google.com/drive/u/0/folders/14rE6xOxQYgXDar_4ymnObTRZJHAj3Bcf**

## How to Use the Project

1. After launching the application, ensure the software has established a proper connection by clicking the **Połącz** (Connect) button. The status of connected modules will be displayed on the top bar (Camera, KURIOS, Platform).
2. Go to the side panel to set the wavelength [nm] and check the preview in **Live View** by clicking **Start Live**.
3. In the right **Presety** (Presets) and **Edytor** (Editor) tabs, you can manage sample settings (dimensions) and objective parameters (FOV).
4. Using the **XYZ** tab, position the platform relative to the specimen so that it is centered under the lens.
5. In the **Skan** (Scan) tab, you can start scanning and use checkboxes for advanced actions:
   - Select `Mapping (trasa XY)` if you want to scan the entire surface of the sample.
   - Select `Focus stack` and define Z points for the system to collect full sharpness from the entire detail.

## Authors

- **Maciej Wróbel, PhD, Eng.** – Project Supervisor
  - Email: maciej.wrobel@pg.edu.pl
- **Hubert Czarnecki** – Project Leader, Software Development
  - Email: 
- **Karol Puczyński** – Software Development
  - Email: karol.puczynski123@gmail.com
- **Piotr Rokita** – Platform Design and Modeling
  - Email: piotr.rok03@gmail.com
- **Patryk Polechoński** – Electronics
  - Email:
