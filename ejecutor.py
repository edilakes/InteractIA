# ejecutor.py
"""
Módulo para la ejecución de código generado por el LLM.
"""
import logging
import pyautogui

def execute_pyautogui_code(codigo: str):
    """
    Ejecuta un string de código Python que utiliza pyautogui.
    CRÍTICO: Esta función es muy potente y debe ser usada con precaución.
    """
    try:
        logging.info(f"Ejecutando código pyautogui: {codigo}")
        # El contexto de exec tiene acceso a 'pyautogui' importado aquí.
        exec(codigo, {"pyautogui": pyautogui})
        return "Ejecución completada con éxito."
    except Exception as e:
        logging.error(f"Error ejecutando código: {e}", exc_info=True)
        return f"Error durante la ejecución: {e}"
