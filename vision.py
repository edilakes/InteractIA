# vision.py
"""
Módulo de Percepción Visual del Agente.
"""
import pyautogui
import logging
from PIL import Image
import os
import sys
import pytesseract
import cv2 # OpenCV para procesamiento de imágenes si es necesario
import numpy as np # Importar numpy

# Configurar la ruta al ejecutable de Tesseract si no está en el PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Ejemplo de ruta en Windows

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

def find_text_on_screen(text: str, confidence: float = 0.7) -> list[dict]:
    """
    Busca una cadena de texto específica en la pantalla usando OCR.
    Retorna una lista de diccionarios con 'box' (coordenadas) y 'confidence' para cada coincidencia.
    """
    logging.info(f"Buscando texto '{text}' en la pantalla con confianza mínima {confidence}...")
    try:
        screenshot = pyautogui.screenshot()
        # Convertir la captura de pantalla a un formato que Tesseract pueda procesar
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Usar image_to_data para obtener información detallada, incluyendo la confianza
        data = pytesseract.image_to_data(img_cv, output_type=pytesseract.Output.DICT)
        
        found_texts = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            # Filtrar por nivel de palabra y confianza
            if int(data['conf'][i]) > (confidence * 100) and data['text'][i].strip():
                word = data['text'][i].strip()
                if text.lower() in word.lower(): # Búsqueda de subcadena insensible a mayúsculas/minúsculas
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    found_texts.append({
                        "box": {"left": x, "top": y, "width": w, "height": h},
                        "text": word,
                        "confidence": float(data['conf'][i]) / 100
                    })
        logging.info(f"Se encontraron {len(found_texts)} ocurrencias del texto '{text}'.")
        return found_texts
    except Exception as e:
        logging.error(f"Error al buscar texto en pantalla: {e}", exc_info=True)
        return []

def find_image_on_screen(image_path: str, confidence: float = 0.9) -> list[dict]:
    """
    Busca una imagen específica en la pantalla.
    Retorna una lista de diccionarios con 'box' (coordenadas) para cada coincidencia.
    """
    logging.info(f"Buscando imagen '{image_path}' en la pantalla con confianza mínima {confidence}...")
    try:
        # pyautogui.locateAllOnScreen devuelve un generador de Box
        locations = list(pyautogui.locateAllOnScreen(image_path, confidence=confidence))
        
        found_images = []
        for loc in locations:
            found_images.append({
                "box": {"left": loc.left, "top": loc.top, "width": loc.width, "height": loc.height}
            })
        logging.info(f"Se encontraron {len(found_images)} ocurrencias de la imagen '{image_path}'.")
        return found_images
    except Exception as e:
        logging.error(f"Error al buscar imagen en pantalla: {e}", exc_info=True)
        return []

def check_window_title(title: str) -> bool:
    """
    Verifica si una ventana con el título especificado está abierta.
    """
    logging.info(f"Verificando si la ventana con título '{title}' está abierta...")
    try:
        windows = pyautogui.getWindowsWithTitle(title)
        if windows:
            logging.info(f"Ventana '{title}' encontrada.")
            return True
        else:
            logging.info(f"Ventana '{title}' no encontrada.")
            return False
    except Exception as e:
        logging.error(f"Error al verificar título de ventana: {e}", exc_info=True)
        return False

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
