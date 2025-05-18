# Controller-Mapper

A lightweight, Python-based application that allows you to use a controller as a mouse, making it possible to navigate your PC without a traditional mouse.
Ideal for browsing the web or casual desktop use from the comfort of your couch.

## Key Features

- Seamless controller-to-mouse mapping  
- Customizable control calibration  
- Simple, plug-and-play experience  
- Compatible with most XInput controllers (e.g., Xbox 360, Xbox One)  

---

## Getting Started

### 1. Installation

To use the precompiled version (recommended), download the latest release:  

- [Download Controller Mouse V1.0](https://github.com/Ronnie-Reagan/Controller-Mapper/releases/download/Controller-Mapper/Controller.Mouse.V1.0.exe)  

Alternatively, run the project from source:  

**Dependencies:**  
- Python 3.12.6 (tested)  
- Required packages: os, json, time, threading, pygame, tkinter, pynput  

Install dependencies with:  
`pip install pygame pynput`
---

### 2. Setup

- Connect your controller to your PC (must be recognized as player 1)  
- Launch the application  
- If no window appears, ensure your controller is connected and recognized as player 1  

---

### 3. Calibrating Controls

- Click "Calibrate Controls" in the app  
- Follow the on-screen prompts to map your desired inputs  
- Note: Settings changed via the GUI are **not saved**  

---

### 4. Manual Configuration (Optional)

For persistent settings, manually edit the **controller_mapping_config.json** file in the root directory. This file is created automatically after the first run.  

---

## Developer Notes

To build the project locally:  
`pyinstaller --onefile --clean --windowed --name "Controller Mouse HomeBrew" mark10.py`
---

### Platform Support

- Designed primarily for Windows (may not function as expected on non-Windows systems)  
- Optimized for right-handed users and Microsoft Xbox 360 controllers  

---

### Known Issues

- Incomplete error handling  
- Potential bugs depending on controller model  

---

## Contributing

Contributions are welcome! If you encounter bugs or have ideas for improvements, feel free to open an issue or submit a pull request.  

---

## License

This project is open-source under the [MIT License](https://github.com/Ronnie-Reagan/Controller-Mapper/tree/main?tab=MIT-1-ov-file#).  

---

Thanks for checking it out and have a good day!
