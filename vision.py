# vision.py
"""
Módulo de Percepción Visual del Agente.
"""
import pyautogui
import logging
from PIL import Image
import os
import sys

# Añadir el directorio raíz al path para poder importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model_manager import get_model_provider

# Prompt para el análisis de la imagen
VISION_PROMPT = """
Eres un experto en análisis de interfaces de usuario (UI). Describe la captura de pantalla proporcionada en detalle.
Identifica todos los elementos visibles, como ventanas, botones, campos de texto, etiquetas, iconos y menús.
Para cada elemento, proporciona una breve descripción y, si es posible, el texto que contiene.
El objetivo es crear un mapa textual de la pantalla que el agente de IA pueda usar para decidir su próxima acción.
"""

def capture_and_analyze_screen() -> str:
    """
    Captura la pantalla, la envía a un modelo multimodal para su análisis y
    devuelve una descripción textual de los elementos presentes.
    """
    logging.info("Iniciando captura y análisis de la pantalla...")

    # 1. Captura de pantalla
    try:
        screenshot = pyautogui.screenshot()
        logging.info("Captura de pantalla realizada con éxito.")
    except Exception as e:
        logging.error(f"Error al tomar la captura de pantalla: {e}")
        return "Error: No se pudo capturar la pantalla."

    # 2. Obtener proveedor del modelo y analizar
    try:
        provider = get_model_provider()
        logging.info(f"Analizando imagen con el proveedor: {provider.provider_type}")
        
        # Asegurarse de que el modelo seleccionado soporta visión
        # Esta es una simplificación; una implementación más robusta verificaría las capacidades del modelo.
        if "vision" not in provider.modelo.model_name:
            logging.warning(f"El modelo por defecto '{provider.modelo.model_name}' podría no ser multimodal. El análisis puede fallar.")

        response = provider.generate_content(prompt=VISION_PROMPT, image=screenshot)
        
        if response and "text" in response:
            description = response["text"]
            logging.info("Análisis de pantalla completado.")
            return description
        else:
            logging.error(f"La respuesta del modelo no fue válida: {response}")
            return "Error: La respuesta del modelo de visión no fue válida."

    except Exception as e:
        logging.error(f"Error durante el análisis de la pantalla con el modelo: {e}", exc_info=True)
        return "Error: Ocurrió un problema al contactar con el modelo de visión."

if __name__ == '__main__':
    # Pequeña prueba para ejecutar el módulo directamente
    logging.basicConfig(level=logging.INFO)
    description = capture_and_analyze_screen()
    print("--- Descripción de la Pantalla ---")
    print(description)
    print("----------------------------------")
