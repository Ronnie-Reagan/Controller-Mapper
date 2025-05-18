import os
import json
import time
import threading
import pygame
import tkinter as tk
from tkinter import messagebox, ttk
from pynput.mouse import Controller as MouseController, Button

# --- Constants ---
CONFIG_FILE = "controller_mapping_config.json"
CALIBRATION_STEPS = [
	("Hold RIGHT stick UP",    "right_stick_vertical_negative", lambda v: v < -0.5),
	("Hold RIGHT stick DOWN",  "right_stick_vertical_positive", lambda v: v >  0.5),
	("Hold RIGHT stick RIGHT", "right_stick_horizontal_positive", lambda v: v >  0.5),
	("Hold RIGHT stick LEFT",  "right_stick_horizontal_negative", lambda v: v < -0.5),
	("Hold LEFT stick UP",     "left_stick_vertical_negative",  lambda v: v < -0.5),
	("Hold LEFT stick DOWN",   "left_stick_vertical_positive",  lambda v: v >  0.5),
	("Hold Right Trigger (L-click)",  "left_trigger_click",  lambda v: v >  0.5),
	("Hold Left Trigger (R-click)",   "right_trigger_click", lambda v: v >  0.5),
	("Hold X (Mouse 3)",      "button_x1", None),
	("Hold Y (Mouse 4)",      "button_x2", None),
]

# --- Application State ---
state = {
	"joystick": None,
	"mouse": None,
	"control_map": {},
	"is_running": False,
	"polling_thread": None,
	# GUI vars will be set in build_ui
}
last_scroll_time = 0

# --- Configuration ---
def load_configuration():
	if not os.path.isfile(CONFIG_FILE):
		return False
	try:
		with open(CONFIG_FILE, 'r') as f:
			data = json.load(f)
		state['control_map'] = {k: tuple(v) for k, v in data.get('control_map', {}).items()}
		state['mouse_speed_var'].set(data.get('mouse_speed', 10))
		state['scroll_speed_var'].set(data.get('scroll_speed', 5))
		state['scroll_clicks_per'].set(data.get('scroll_clicks_per', 0.2))
		state['deadzone_var'].set(data.get('deadzone', 0.2))
		return True
	except Exception:
		return False


def save_configuration():
	data = {
		'control_map': state['control_map'],
		'mouse_speed': state['mouse_speed_var'].get(),
		'scroll_speed': state['scroll_speed_var'].get(),
		'scroll_clicks_per': state['scroll_clicks_per'].get(),
		'deadzone': state['deadzone_var'].get(),
	}
	with open(CONFIG_FILE, 'w') as f:
		json.dump(data, f, indent=2)

# --- Joystick Initialization ---
def init_joystick(status_label):
	pygame.init()
	status_label.config(text="Waiting for joystick…")
	global initial_loading
	if pygame.joystick.get_count() == 0 and initial_loading == True:
		initial_loading = False
		if messagebox.askyesno("Controller Detection Failed", "No controller detected, Please connect your controller before closing this pop-up."):
			time.sleep(1)
			if pygame.joystick.get_count() == 0:
				time.sleep(9999)
	while pygame.joystick.get_count() == 0:
		pygame.event.pump()
		time.sleep(0.5)
	js = pygame.joystick.Joystick(0)
	js.init()
	state['joystick'] = js
	status_label.config(text=f"Joystick connected: {js.get_name()}")

def filter_deadzone(value):
	dz = state['deadzone_var'].get()
	if abs(value) <= dz:
		return 0.0
	
	# Smooth exponential scaling for finer control near center
	normalized = (abs(value) - dz) / (1 - dz)
	scaled = normalized ** 2  # Use a quadratic curve for smoother ramp-up
	return scaled * (1 if value > 0 else -1)

def prompt_and_detect_control(prompt, predicate):
	messagebox.showinfo("Calibration", prompt)
	js = state['joystick']
	while True:
		pygame.event.pump()
		if predicate:
			for i in range(js.get_numaxes()):
				v = filter_deadzone(js.get_axis(i))
				if predicate(v):
					return i, (1 if v > 0 else -1)
		else:
			for i in range(js.get_numbuttons()):
				if js.get_button(i):
					return i, None
		time.sleep(0.01)

# --- Calibration Workflow ---
def calibrate_controls(mapping_display, start_btn, status_label):
	start_btn.state(['disabled'])
	state['control_map'].clear()
	for prompt, key, pred in CALIBRATION_STEPS:
		idx, pol = prompt_and_detect_control(prompt, pred)
		state['control_map'][key] = (idx, pol)
	refresh_mapping_display(mapping_display)
	status_label.config(text="Status: Ready")
	save_configuration()
	start_btn.state(['!disabled'])


def refresh_mapping_display(mapping_display):
	mapping_display.delete('1.0', tk.END)
	for key, (idx, pol) in state['control_map'].items():
		mapping_display.insert(tk.END, f"{key}: idx={idx}, pol={pol}\n")

# --- Polling Helpers ---
def check_reconnect(status_label):
	"""
	Checks for joystick disconnection, reconnects and updates status.
	Returns True if reconnection occurred.
	"""
	if pygame.joystick.get_count() == 0:
		status_label.config(text="Joystick disconnected")
		init_joystick(status_label)
		status_label.config(text="Joystick reconnected")
		return True
	return False

def old_filter_deadzone(value):
    dz = state['deadzone_var'].get()
    return value if abs(value) > dz else 0.0

def process_mouse_movement(js, mouse):
	"""
	Processes right-stick axes into mouse movement.
	"""
	cm = state['control_map']
	try:
		xi, xp = cm['right_stick_horizontal_positive']
		yi, yp = cm['right_stick_vertical_positive']
		x = old_filter_deadzone(js.get_axis(xi)) * xp
		y = old_filter_deadzone(js.get_axis(yi)) * yp
		if x or y:
			dx = int(x * state['mouse_speed_var'].get())
			dy = int(y * state['mouse_speed_var'].get())
			mouse.move(dx, dy)
	except KeyError:
		pass


def process_scroll(js, mouse):
	global last_scroll_time
	cm = state['control_map']
	
	try:
		si, sp = cm['left_stick_vertical_negative']
		raw = -js.get_axis(si)
		
		dz = state['deadzone_var'].get()
		if abs(raw) <= dz:
			return
		
		
		direction = -state["scroll_clicks_per"].get() * -raw if raw < 0 else state["scroll_clicks_per"].get() * raw
		mouse.scroll(0, direction)
			
	except KeyError:
		pass

def process_button_presses(js, mouse, prev_states):
	"""
	Processes button and trigger presses into mouse click/release events.
	"""
	cm = state['control_map']
	for key, btn in [
		('left_trigger_click', Button.left),
		('right_trigger_click', Button.right),
		('button_x1', Button.x1),
		('button_x2', Button.x2),
	]:
		if key not in cm:
			continue
		idx, pol = cm[key]
		raw = (js.get_axis(idx) * pol
			   if key.endswith('_click') else
			   (1 if js.get_button(idx) else 0))
		pressed = raw > 0
		if pressed and not prev_states.get(key, False):
			mouse.press(btn)
		elif not pressed and prev_states.get(key, False):
			mouse.release(btn)
		prev_states[key] = pressed

# --- Polling Loop ---
def polling_loop(start_btn, stop_btn, status_label):
	"""
	Main polling loop: handles reconnection, movement, scrolling, clicking.
	"""
	prev_states = {}
	js = state['joystick']
	mouse = state['mouse']
	while state['is_running']:
		pygame.event.pump()
		if check_reconnect(status_label):
			continue
		process_mouse_movement(js, mouse)
		process_scroll(js, mouse)
		process_button_presses(js, mouse, prev_states)
		time.sleep(0.01)

	# Cleanup UI state
	status_label.config(text="Status: Idle")
	stop_btn.state(['disabled'])
	start_btn.state(['!disabled'])

# --- Start/Stop Handlers ---
def start_mapping(start_btn, stop_btn, status_label):
	if not state['control_map']:
		messagebox.showwarning("Warning", "Please calibrate controls first.")
		return
	state['is_running'] = True
	start_btn.state(['disabled'])
	stop_btn.state(['!disabled'])
	status_label.config(text="Status: Running")
	t = threading.Thread(target=polling_loop,
						 args=(start_btn, stop_btn, status_label),
						 daemon=True)
	state['polling_thread'] = t
	t.start()


def stop_mapping():
	state['is_running'] = False

# --- UI Construction ---
def build_ui():
	root = tk.Tk()
	root.title("Controller to Mouse Mapper")
	root.attributes('-topmost', True)  # Force on top
	root.after(500, lambda: root.attributes('-topmost', False)) #500ms delay for removal from top

	frame = ttk.Frame(root, padding=10)
	frame.grid(sticky='nsew')

	status_label = ttk.Label(frame, text="SYSTEM LOADING")
	status_label.grid(row=0, column=0, columnspan=2, pady=(0,5))


	# State variables
	state['mouse_speed_var'] = tk.DoubleVar(value=10)
	state['scroll_speed_var'] = tk.DoubleVar(value=5)
	state['scroll_clicks_per'] = tk.DoubleVar(value=0.2)
	state['deadzone_var'] = tk.DoubleVar(value=0.2)

	# Calibration and mapping display
	mapping_display = tk.Text(frame, height=8, width=40)
	mapping_display.grid(row=1, column=0, columnspan=2, pady=5)

	# Parameter sliders
	ttk.Label(frame, text="Mouse Speed (1 - 50)").grid(row=2, column=0, sticky='w')
	ttk.Scale(frame, from_=1, to=50,
			  variable=state['mouse_speed_var'], orient='horizontal').grid(row=3, column=0, sticky='ew')
	
	ttk.Label(frame, text="NOT IN USE").grid(row=2, column=1, sticky='w')
	ttk.Scale(frame, from_=1, to=10,
			  variable=state['scroll_speed_var'], orient='horizontal').grid(row=3, column=1, sticky='ew')
	
	ttk.Label(frame, text="Scroll Speed").grid(row=4, column=1, sticky='w')
	ttk.Scale(frame, from_=0.01, to=1.0,
			  variable=state['scroll_clicks_per'], orient='horizontal').grid(row=5, column=1, sticky='ew')
	
	ttk.Label(frame, text="Deadzone (0 - 0.5)").grid(row=4, column=0, sticky='w')
	ttk.Scale(frame, from_=0.0, to=0.5,
			  variable=state['deadzone_var'], orient='horizontal').grid(row=5, column=0, sticky='ew')

# Control buttons
	start_btn = ttk.Button(frame, text="Start",
						   command=lambda: start_mapping(start_btn, stop_btn, status_label))
	stop_btn  = ttk.Button(frame, text="Stop", command=stop_mapping)
	start_btn.grid(row=6, column=0, pady=10, padx=(0,5))
	stop_btn.grid(row=6, column=1, pady=10)
	stop_btn.state(['disabled'])

	calibrate_btn = ttk.Button(frame, text="Calibrate Controls",
								command=lambda: calibrate_controls(mapping_display, start_btn, status_label))
	calibrate_btn.grid(row=7, column=0, columnspan=2, pady=(0,10))

	# Close handler
	root.protocol("WM_DELETE_WINDOW", lambda: on_close(root))
	init_joystick(status_label)
	return root, mapping_display, start_btn, stop_btn, status_label


def on_close(root):
	state['is_running'] = False
	t = state.get('polling_thread')
	if t and t.is_alive():
		t.join(timeout=1)
	pygame.quit()
	root.destroy()

try:
	initial_loading = True
	state['mouse'] = MouseController()
	root, mapping_display, start_btn, stop_btn, status_label = build_ui()
	initial_loading = False
	if load_configuration() and messagebox.askyesno("Load Configuration",
												   "Load saved settings?\n"
												   "The app will automatically start running if Yes."):
		refresh_mapping_display(mapping_display)
		start_mapping(start_btn, stop_btn, status_label)

	root.mainloop()

except Exception as e:
	messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{e}\n\nSend this to keef_it_up on Discord")