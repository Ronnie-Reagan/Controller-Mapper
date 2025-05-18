# Controller-Mapper

Simple python based app to allow using a controller as a mouse input.
feel free to surf the web _sans mouse_!

if you want the plug and play download, [click me](https://github.com/Ronnie-Reagan/Controller-Mapper/releases/download/Controller-Mapper/Controller.Mouse.V1.0.exe) for version 1.0

Dev Stuff below

Dependencies to run locally:
  - python(I used 3.12.6)
  - os
  - json
  - time
  - threading
  - pygame
  - tkinter
  - pynput

Created Files:
  root/controller_mapping_config.json

May not function as expected on a non-windows machine

I used pyinstaller to compile the exe with the following command+args
  `pyinstaller --onefile --clean --windowed --name "Controller Mouse V1.0" mark10.py`

Designed and tested for right handed people and the XInput input from a Microsoft Authentic Xbox 360 controller

It has various bugs and errors but you know what? it works on my machine!

Thanks for checking it out and have a good day :)
