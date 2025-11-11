# grabador.py

import logging
from pynput import mouse, keyboard
import time

_is_recording = False
_recorded_actions = []
_logger = logging.getLogger("InteractIA")

_mouse_listener = None
_keyboard_listener = None

def on_click(x, y, button, pressed):
    global _is_recording
    if _is_recording and pressed:
        # pyautogui.position() returns current mouse position, but pynput's on_click already gives x, y
        # We need to convert these absolute coordinates to relative if the agent uses relative coordinates.
        # For now, we'll record absolute coordinates.
        record_action("clic", {"x": x, "y": y, "boton": str(button).split('.')[-1]})

def on_press(key):
    global _is_recording
    if _is_recording:
        try:
            # Handle alphanumeric keys
            record_action("presionar_tecla", {"tecla": key.char})
        except AttributeError:
            # Handle special keys (e.g., space, enter, shift)
            record_action("presionar_tecla", {"tecla": str(key).split('.')[-1]})

def start_recording():
    global _is_recording, _recorded_actions, _mouse_listener, _keyboard_listener
    _is_recording = True
    _recorded_actions = []
    _logger.info("Grabación de acciones iniciada.")

    # Start mouse listener
    _mouse_listener = mouse.Listener(on_click=on_click)
    _mouse_listener.start()

    # Start keyboard listener
    _keyboard_listener = keyboard.Listener(on_press=on_press)
    _keyboard_listener.start()

def stop_recording():
    global _is_recording, _mouse_listener, _keyboard_listener
    _is_recording = False
    _logger.info("Grabación de acciones detenida.")

    if _mouse_listener:
        _mouse_listener.stop()
        _mouse_listener.join() # Wait for the listener to finish
        _mouse_listener = None

    if _keyboard_listener:
        _keyboard_listener.stop()
        _keyboard_listener.join() # Wait for the listener to finish
        _keyboard_listener = None
        
    return _recorded_actions

def record_action(action_name: str, args: dict):
    if _is_recording:
        _recorded_actions.append({"accion": action_name, "argumentos": args})
        _logger.debug(f"Acción grabada: {action_name} con args {args}")

def is_recording() -> bool:
    return _is_recording