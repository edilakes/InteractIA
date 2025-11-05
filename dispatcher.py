# dispatcher.py
"""
Este módulo se encarga de parsear la respuesta del LLM
y despachar la acción correspondiente a la función adecuada.
"""

import ejecutor
# Aquí se importarían otros módulos de acción como 'vision', 'memoria', etc.

# Mapeo de acciones a funciones
ACTION_MAP = {
    "ejecutar_pyautogui": lambda args: ejecutor.execute_pyautogui_code(args.get("codigo")),
    # "responder_chat": lambda args: comunicador.send_message(args.get("mensaje")),
    # "analizar_pantalla": lambda args: vision.capture_and_analyze_screen(),
    # "consultar_base_conocimiento": lambda args: memoria.query_base_conocimiento(args.get("termino_busqueda")),
}

def dispatch_action(action_name: str, arguments: dict):
    """Busca la acción en el mapa y la ejecuta con sus argumentos."""
    if action_name in ACTION_MAP:
        return ACTION_MAP[action_name](arguments)
    else:
        raise ValueError(f"Acción desconocida: {action_name}")
