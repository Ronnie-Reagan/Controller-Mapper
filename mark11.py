import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import pygame
from pynput import keyboard as pkb, mouse as pm

CONFIG_FILE = "controller_to_keyboard_bindings.json"

# --- State ---
state = {
    "joystick": None,
    "mappings": {},  # { "input_id": "keyboard_key" }
    "polling": False,
    "keyboard_state": set(),
}

# --- Initialize pygame joystick ---
pygame.init()
pygame.joystick.init()

def detect_joystick():
    if pygame.joystick.get_count() == 0:
        return None
    js = pygame.joystick.Joystick(0)
    js.init()
    return js

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            state["mappings"] = json.load(f)
    except:
        state["mappings"] = {}

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(state["mappings"], f, indent=2)

# --- Keyboard simulation ---
keyboard_controller = pkb.Controller()
mouse_controller = pm.Controller()

def press_key(key):
    try:
        if key.startswith("mouse_button:"):
            button_name = key.split(":")[1]
            button = getattr(pm.Button, button_name, None)
            if button:
                mouse_controller.press(button)
        elif key.startswith("mouse:"):
            # Mouse direction (simulate movement)
            dx = dy = 0
            if key == "mouse:left": dx = -20
            elif key == "mouse:right": dx = 20
            elif key == "mouse:up": dy = -20
            elif key == "mouse:down": dy = 20
            mouse_controller.move(dx, dy)
        else:
            keyboard_controller.press(key)
    except Exception as e:
        print("Error pressing key:", key, e)

def release_key(key):
    try:
        if key.startswith("mouse_button:"):
            button_name = key.split(":")[1]
            button = getattr(pm.Button, button_name, None)
            if button:
                mouse_controller.release(button)
        elif key.startswith("mouse:"):
            # Directional mouse movement doesn't need release
            return
        else:
            keyboard_controller.release(key)
    except Exception as e:
        print("Error releasing key:", key, e)


debounce_timers = {}  # input_id: time remaining
debounce_steps = {}   # input_id: step count for repeated presses

def polling_loop():
    js = state["joystick"]
    keyboard_state = state["keyboard_state"]
    mappings = state["mappings"]

    debounce_timers = {}
    debounce_steps = {}

    interval = 0.01  # 10ms
    min_interval = 0.1
    base_interval = 0.8

    while state["polling"]:
        pygame.event.pump()
        for input_id, key in mappings.items():
            parts = input_id.split(":")
            input_type = parts[0]
            idx = int(parts[1])
            pressed = False

            if input_type == "axis":
                polarity = int(parts[2])
                val = js.get_axis(idx)
                threshold = 0.5
                if polarity > 0:
                    pressed = val > threshold
                else:
                    pressed = val < -threshold
            elif input_type == "button":
                pressed = js.get_button(idx) == 1
            else:
                continue

            debounce = debounce_timers.get(input_id, 0)
            step = debounce_steps.get(input_id, 0)

            if pressed:
                if debounce <= 0:
                    if key not in keyboard_state:
                        keyboard_state.add(key)
                    step += 1
                    interval_time = max(base_interval - step * 0.1, min_interval)
                    debounce_timers[input_id] = interval_time
                    debounce_steps[input_id] = step
                    press_key(key)
                else:
                    debounce_timers[input_id] = debounce - interval
            else:
                if key in keyboard_state:
                    release_key(key)
                    keyboard_state.remove(key)
                debounce_timers[input_id] = 0
                debounce_steps[input_id] = 0

        time.sleep(interval)

# --- GUI ---
class App:
    def __init__(self, root):
        self.root = root
        root.title("Controller to Keyboard Mapper")

        self.js = detect_joystick()
        if not self.js:
            messagebox.showerror("Error", "No joystick detected. Please connect a controller and restart.")
            root.destroy()
            return
        state["joystick"] = self.js

        self.mapping_list = tk.Listbox(root, width=50)
        self.mapping_list.grid(row=0, column=0, columnspan=3, pady=5)

        self.add_btn = ttk.Button(root, text="Add Binding", command=self.add_binding)
        self.add_btn.grid(row=1, column=0, pady=5, sticky="ew")

        self.remove_btn = ttk.Button(root, text="Remove Selected", command=self.remove_selected)
        self.remove_btn.grid(row=1, column=1, pady=5, sticky="ew")

        self.start_btn = ttk.Button(root, text="Start Mapping", command=self.start_mapping)
        self.start_btn.grid(row=1, column=2, pady=5, sticky="ew")

        self.stop_btn = ttk.Button(root, text="Stop Mapping", command=self.stop_mapping, state="disabled")
        self.stop_btn.grid(row=2, column=2, pady=5, sticky="ew")

        self.status = ttk.Label(root, text="Joystick detected: " + self.js.get_name())
        self.status.grid(row=2, column=0, columnspan=2, sticky="w")

        load_config()
        self.refresh_listbox()

    def refresh_listbox(self):
        self.mapping_list.delete(0, tk.END)
        for input_id, key in state["mappings"].items():
            self.mapping_list.insert(tk.END, f"{input_id} → {key}")

    def add_binding(self):
        # Step 1: Select controller input
        input_id = self.get_controller_input()
        if input_id is None:
            return
    
        # Step 2: Ask user which input type to bind to
        def choose_input_type():
            prompt = tk.Toplevel(self.root)
            prompt.title("Choose Input Type")
            ttk.Label(prompt, text="Select the type of input to bind to:").pack(padx=10, pady=10)
    
            result = tk.StringVar()
    
            def choose(option):
                result.set(option)
                prompt.destroy()
    
            ttk.Button(prompt, text="Keyboard Key", command=lambda: choose("keyboard")).pack(padx=10, pady=5, fill="x")
            ttk.Button(prompt, text="Mouse Direction", command=lambda: choose("mouseXY")).pack(padx=10, pady=5, fill="x")
            ttk.Button(prompt, text="Mouse Button", command=lambda: choose("mouseB")).pack(padx=10, pady=5, fill="x")
    
            prompt.grab_set()
            prompt.wait_window()
            return result.get()
    
        selected_type = choose_input_type()
        if not selected_type:
            return
    
        # Step 3: Collect selected input
        if selected_type == "keyboard":
            result = self.get_keyboard_key()
        elif selected_type == "mouseXY":
            result = self.get_mouse_direction()
        elif selected_type == "mouseB":
            result = self.get_mouse_buttons()
        else:
            return
    
        if result is None:
            return
    
        state["mappings"][input_id] = result
        save_config()
        self.refresh_listbox()
    

    def remove_selected(self):
        sel = self.mapping_list.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.mapping_list.get(idx)
        input_id = key.split(" → ")[0]
        if input_id in state["mappings"]:
            del state["mappings"][input_id]
            save_config()
            self.refresh_listbox()

    def get_controller_input(self):
        prompt = tk.Toplevel(self.root)
        prompt.title("Select Controller Input")
        ttk.Label(prompt, text="Move an axis or press a button on your controller").pack(padx=10, pady=10)
        input_var = tk.StringVar(value="")

        trigger_axes = {4, 5}
        threshold = 0.75

        def poll_input():
            pygame.event.pump()
            for i in range(self.js.get_numbuttons()):
                if self.js.get_button(i):
                    input_var.set(f"button:{i}")
                    return True
            for i in range(self.js.get_numaxes()):
                val = self.js.get_axis(i)
                if i in trigger_axes:
                    if val > threshold:
                        input_var.set(f"axis:{i}:1")
                        return True
                else:
                    if val > threshold:
                        input_var.set(f"axis:{i}:1")
                        return True
                    elif val < -threshold:
                        input_var.set(f"axis:{i}:-1")
                        return True
            return False

        def check_input():
            if poll_input():
                prompt.destroy()
            else:
                prompt.after(50, check_input)

        prompt.after(50, check_input)
        prompt.grab_set()
        prompt.wait_window()
        return input_var.get() if input_var.get() else None

    def get_keyboard_key(self):
        prompt = tk.Toplevel(self.root)
        prompt.title("Press Keyboard Key")
        ttk.Label(prompt, text="Press the keyboard key to bind").pack(padx=10, pady=10)
        key_var = tk.StringVar(value="")

        def on_key(event):
            key_var.set(event.keysym.lower())
            prompt.destroy()

        prompt.bind("<Key>", on_key)
        prompt.grab_set()
        prompt.wait_window()
        return key_var.get() if key_var.get() else None

    def get_mouse_direction(self):
        prompt = tk.Toplevel(self.root)
        prompt.title("Move Mouse")
        ttk.Label(prompt, text="Move the mouse to bind a direction").pack(padx=10, pady=10)

        initial = mouse_controller.position
        move_var = tk.StringVar()

        def detect_movement():
            current = mouse_controller.position
            dx, dy = current[0] - initial[0], current[1] - initial[1]
            if abs(dx) > 20:
                move_var.set("mouse:right" if dx > 0 else "mouse:left")
                prompt.destroy()
            elif abs(dy) > 20:
                move_var.set("mouse:down" if dy > 0 else "mouse:up")
                prompt.destroy()
            else:
                prompt.after(50, detect_movement)

        prompt.after(50, detect_movement)
        prompt.grab_set()
        prompt.wait_window()
        return move_var.get() if move_var.get() else None

    def get_mouse_buttons(self):
        prompt = tk.Toplevel(self.root)
        prompt.title("Click Mouse Button")
        ttk.Label(prompt, text="Click a mouse button to bind").pack(padx=10, pady=10)

        btn_var = tk.StringVar()

        def on_click(x, y, button, pressed):
            if pressed:
                btn_var.set(f"mouse_button:{button.name}")
                prompt.destroy()
                return False

        listener = pm.Listener(on_click=on_click)
        listener.start()

        prompt.grab_set()
        prompt.wait_window()
        listener.stop()

        return btn_var.get() if btn_var.get() else None

    def start_mapping(self):
        if state["polling"]:
            return
        state["polling"] = True
        self.status.config(text="Mapping started")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.poll_thread = threading.Thread(target=polling_loop, daemon=True)
        self.poll_thread.start()

    def stop_mapping(self):
        if not state["polling"]:
            return
        state["polling"] = False
        self.status.config(text="Mapping stopped")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
