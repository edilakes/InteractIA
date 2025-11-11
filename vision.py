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
import json
import re

# Configurar la ruta al ejecutable de Tesseract si no está en el PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\ Program Files\Tesseract-OCR\tesseract.exe' # Ejemplo de ruta en Windows

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

VERIFICATION_PROMPT = """
Eres un asistente de verificación. Tu tarea es determinar si la imagen proporcionada coincide con la descripción del resultado esperado.
La descripción es: "{expected_outcome}"

Analiza la imagen y responde ÚNICAMENTE con un objeto JSON que contenga:
- "is_verified": true si la imagen coincide con la descripción, false en caso contrario.
- "explanation": Una breve explicación de tu decisión.
- "confidence_score": Un valor flotante entre 0.0 y 1.0 que represente tu confianza en la verificación.

Ejemplo de respuesta JSON:
```json
{{
  "is_verified": true,
  "explanation": "La calculadora de Windows está abierta y visible.",
  "confidence_score": 0.98
}}
```
"""

def find_text_on_screen(text: str, confidence: float = 0.7) -> list[dict]:
    """
    Busca una cadena de texto específica en la pantalla usando OCR.
    Retorna una lista de diccionarios con 'box' (coordenadas) y 'confidence' para cada coincidencia.
    """
    logging.info(f"Buscando texto '{text}' en la pantalla con confianza mínima {confidence}...")
    try:
        screenshot = pyautogui.screenshot()
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        data = pytesseract.image_to_data(img_cv, output_type=pytesseract.Output.DICT)
        
        found_texts = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > (confidence * 100) and data['text'][i].strip():
                word = data['text'][i].strip()
                if text.lower() in word.lower():
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
        locations = list(pyautogui.locateAllOnScreen(image_path, confidence=confidence))
        found_images = [{"box": {"left": loc.left, "top": loc.top, "width": loc.width, "height": loc.height}} for loc in locations]
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
        return bool(pyautogui.getWindowsWithTitle(title))
    except Exception as e:
        logging.error(f"Error al verificar título de ventana: {e}", exc_info=True)
        return False

def capture_and_analyze_screen(screenshot_path: str = None) -> str:
    """
    Captura la pantalla o usa una imagen existente, la envía a un modelo multimodal 
    para su análisis y devuelve una descripción textual de los elementos presentes.
    """
    logging.info("Iniciando captura y análisis de la pantalla...")
    image_to_analyze = None
    if screenshot_path:
        try:
            image_to_analyze = Image.open(screenshot_path)
            logging.info(f"Usando captura de pantalla existente: {screenshot_path}")
        except FileNotFoundError:
            logging.error(f"No se encontró el archivo de captura de pantalla: {screenshot_path}")
            return "Error: No se pudo encontrar el archivo de captura de pantalla."
    else:
        try:
            image_to_analyze = pyautogui.screenshot()
            logging.info("Captura de pantalla realizada con éxito.")
        except Exception as e:
            logging.error(f"Error al tomar la captura de pantalla: {e}")
            return "Error: No se pudo capturar la pantalla."

    try:
        provider = get_model_provider()
        logging.info(f"Analizando imagen con el proveedor: {provider.provider_type}")
        
        if "vision" not in provider.modelo.model_name:
            logging.warning(f"El modelo por defecto '{provider.modelo.model_name}' podría no ser multimodal.")

        response = provider.generate_content(prompt=VISION_PROMPT, image=image_to_analyze)
        
        if response and "text" in response:
            return response["text"]
        else:
            logging.error(f"La respuesta del modelo no fue válida: {response}")
            return "Error: La respuesta del modelo de visión no fue válida."

    except Exception as e:
        logging.error(f"Error durante el análisis de la pantalla con el modelo: {e}", exc_info=True)
        return "Error: Ocurrió un problema al contactar con el modelo de visión."

def verify_image_with_description(image_path: str, expected_outcome: str) -> dict:
    """
    Usa un modelo de visión para verificar si una imagen coincide con una descripción.
    """
    logging.info(f"Verificando si la imagen '{image_path}' coincide con la descripción: '{expected_outcome}'")
    
    try:
        image = Image.open(image_path)
    except FileNotFoundError:
        logging.error(f"No se encontró el archivo de imagen para verificación: {image_path}")
        return {"verificado": False, "confianza": 0.0, "razon": "No se encontró el archivo de imagen."}

    try:
        provider = get_model_provider()
        prompt = VERIFICATION_PROMPT.format(expected_outcome=expected_outcome)
        response = provider.generate_content(prompt=prompt, image=image)
        
        if response and "text" in response:
            # Extraer el JSON de la respuesta del modelo
            json_str = response["text"]
            match = re.search(r'```json\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
            
            try:
                verification_data = json.loads(json_str)
                return {
                    "verificado": verification_data.get("is_verified", False),
                    "confianza": verification_data.get("confidence_score", 0.0),
                    "razon": verification_data.get("explanation", "No se proporcionó explicación del modelo.")
                }
            except json.JSONDecodeError:
                logging.error(f"No se pudo decodificar el JSON de la respuesta de verificación: {json_str}")
                return {"verificado": False, "confianza": 0.0, "razon": "La respuesta del modelo de verificación no fue un JSON válido."}
        else:
            logging.error(f"La respuesta del modelo de verificación no fue válida: {response}")
            return {"verificado": False, "confianza": 0.0, "razon": "Respuesta inválida del modelo de verificación."}

    except Exception as e:
        logging.error(f"Error durante la verificación de la imagen con el modelo: {e}", exc_info=True)
        return {"verificado": False, "confianza": 0.0, "razon": f"Error técnico durante la verificación: {e}"}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # description = capture_and_analyze_screen()
    # print("---" Descripción de la Pantalla ---")
    # print(description)
    # print("----------------------------------")

    # Ejemplo de cómo usar la nueva función de verificación
    # Necesitarías una imagen llamada 'test_image.png' para que esto funcione
    # if os.path.exists("test_image.png"):
    #     outcome = "Se ve una ventana del explorador de archivos de Windows."
    #     verification_result = verify_image_with_description("test_image.png", outcome)
    #     print("\n--- Resultado de la Verificación ---")
    #     print(verification_result)
    #     print("------------------------------------")
    # else:
    #     print("\nCrea un archivo 'test_image.png' para probar la función de verificación.")
    print("Módulo de visión cargado.")
