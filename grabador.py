# grabador.py

import logging

_is_recording = False
_recorded_actions = []
_logger = logging.getLogger("InteractIA")

def start_recording():
    global _is_recording, _recorded_actions
    _is_recording = True
    _recorded_actions = []
    _logger.info("Grabación de acciones iniciada.")

def stop_recording():
    global _is_recording
    _is_recording = False
    _logger.info("Grabación de acciones detenida.")
    return _recorded_actions

def record_action(action_name: str, args: dict):
    if _is_recording:
        _recorded_actions.append({"accion": action_name, "argumentos": args})
        _logger.debug(f"Acción grabada: {action_name} con args {args}")

def is_recording() -> bool:
    return _is_recording
