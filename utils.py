# utils.py
import time
import logging
from vision import find_text_on_screen, find_image_on_screen, check_window_title

_logger = logging.getLogger("InteractIA")

def wait_for_condition(condition_type: str, value: str, timeout: int = 10, interval: float = 0.5) -> bool:
    """
    Espera hasta que se cumpla una condición visual o de estado de ventana.

    Args:
        condition_type (str): Tipo de condición a esperar ('text_present', 'image_present', 'window_open').
        value (str): El texto, la ruta de la imagen o el título de la ventana a buscar.
        timeout (int): Tiempo máximo de espera en segundos.
        interval (float): Intervalo entre comprobaciones en segundos.

    Returns:
        bool: True si la condición se cumple dentro del tiempo de espera, False en caso contrario.
    """
    _logger.info(f"Esperando condición '{condition_type}' con valor '{value}' (timeout: {timeout}s)")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_type == "text_present":
            if find_text_on_screen(value):
                _logger.info(f"Condición 'text_present' ('{value}') cumplida.")
                return True
        elif condition_type == "image_present":
            if find_image_on_screen(value):
                _logger.info(f"Condición 'image_present' ('{value}') cumplida.")
                return True
        elif condition_type == "window_open":
            if check_window_title(value):
                _logger.info(f"Condición 'window_open' ('{value}') cumplida.")
                return True
        else:
            _logger.warning(f"Tipo de condición desconocido: {condition_type}")
            return False
        
        time.sleep(interval)
    
    _logger.warning(f"Tiempo de espera agotado para la condición '{condition_type}' con valor '{value}'.")
    return False
