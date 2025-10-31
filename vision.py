import pyautogui
from PIL import Image, ImageDraw
import logging
import pytesseract
import os
import time

def buscar_tesseract_en_sistema():
    """
    Busca el ejecutable de Tesseract en rutas comunes y en el PATH del sistema.
    Devuelve la ruta completa si lo encuentra, de lo contrario None.
    """
    logging.info("Buscando Tesseract OCR...")
    
    # 1. Rutas de instalación comunes para Windows
    rutas_comunes = [
        "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        os.path.expanduser("~\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe")
    ]
    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            logging.info(f"(+) Tesseract encontrado en ruta común: {ruta}")
            return ruta

    # 2. Buscar en el PATH del sistema
    try:
        import shutil
        ruta_en_path = shutil.which("tesseract")
        if ruta_en_path:
            logging.info(f"(+) Tesseract encontrado en el PATH: {ruta_en_path}")
            return ruta_en_path
    except ImportError:
        logging.warning("shutil.which no está disponible. Omitiendo búsqueda en PATH.")

    logging.warning("(-) Tesseract no se encontró en rutas comunes ni en el PATH.")
    return None

class Vision:
    """
    Clase encargada de la percepción del entorno, incluyendo captura de pantalla y OCR.
    """
    def __init__(self):
        self.logger = logging.getLogger("InteractIA")
        try:
            tesseract_path = buscar_tesseract_en_sistema()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.logger.info(f"Usando Tesseract desde la ruta: {tesseract_path}")
                self.ocr_disponible = True
            else:
                self.logger.error("Tesseract OCR no fue encontrado. La funcionalidad de lectura de pantalla no estará disponible.")
                self.ocr_disponible = False
        except Exception as e:
            self.logger.error(f"Error crítico al configurar Pytesseract: {e}", exc_info=True)
            self.ocr_disponible = False

    def capturar_entorno(self, id_ventana_propia=None):
        """Captura la pantalla completa, ocultando temporalmente la ventana propia del agente."""
        self.logger.debug("Capturando el entorno (ocultando ventana propia).")
        
        ventana_propia = None
        if id_ventana_propia:
            try:
                # Usamos una coincidencia más flexible para el título
                all_windows = pyautogui.getAllWindows()
                ventanas_coincidentes = [w for w in all_windows if id_ventana_propia in w.title]
                
                if ventanas_coincidentes:
                    ventana_propia = ventanas_coincidentes[0]
                    # Minimizamos en lugar de ocultar para mayor compatibilidad
                    ventana_propia.minimize()
                    time.sleep(0.2)  # Pausa para asegurar que la ventana se minimice
                else:
                    self.logger.warning(f"No se encontró la ventana propia para ocultar: '{id_ventana_propia}'")
            except Exception as e:
                self.logger.error(f"Error al minimizar la ventana propia '{id_ventana_propia}': {e}")
                # Si falla, continuamos para no bloquear al agente, pero la captura puede incluir la GUI.

        captura_completa = pyautogui.screenshot()

        if ventana_propia:
            try:
                # Restauramos la ventana
                ventana_propia.restore()
            except Exception as e:
                self.logger.error(f"Error al restaurar la ventana propia '{id_ventana_propia}': {e}")

        return captura_completa

    def leer_texto_en_pantalla(self, imagen: Image.Image):
        """
        Utiliza OCR para extraer texto y sus coordenadas de una imagen.
        """
        if not self.ocr_disponible:
            self.logger.warning("Intento de leer texto sin OCR disponible. Devolviendo lista vacía.")
            return []

        self.logger.info("Realizando OCR para leer texto en la imagen.")
        try:
            data = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT, lang='spa+eng')
            
            bloques = []
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                confianza = int(data['conf'][i])
                if confianza > 50: # Umbral de confianza ajustado
                    texto = data['text'][i].strip()
                    if texto:
                        bloque = {
                            'texto': texto,
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': confianza
                        }
                        bloques.append(bloque)
            
            self.logger.info(f"OCR completado. Se encontraron {len(bloques)} bloques de texto.")
            return bloques
        except pytesseract.TesseractNotFoundError:
            self.logger.error("Tesseract no encontrado durante el OCR. Esto no debería ocurrir si la inicialización fue correcta.")
            self.ocr_disponible = False # Marcamos como no disponible para futuros intentos
            return []
        except Exception as e:
            self.logger.error(f"Ocurrió un error durante el OCR: {e}", exc_info=True)
            return []

    # --- Métodos existentes sin cambios importantes ---
    def capturar_ventana_objetivo(self, titulo_objetivo):
        self.logger.debug(f"Intentando capturar la ventana objetivo: {titulo_objetivo}")
        try:
            ventanas = pyautogui.getWindowsWithTitle(titulo_objetivo)
            if ventanas:
                ventana = ventanas[0]
                region = (ventana.left, ventana.top, ventana.width, ventana.height)
                # Asegurarse de que la región es válida
                if region[2] > 0 and region[3] > 0:
                    captura_ventana = pyautogui.screenshot(region=region)
                    self.logger.info(f"Capturada la ventana objetivo: '{titulo_objetivo}'")
                    return captura_ventana
                else:
                    self.logger.warning(f"La ventana '{titulo_objetivo}' tiene dimensiones no válidas para captura.")
                    return None
            else:
                self.logger.warning(f"No se encontró ninguna ventana con el título: '{titulo_objetivo}'")
                return None
        except Exception as e:
            self.logger.error(f"Error al capturar la ventana '{titulo_objetivo}': {e}")
            return None

    def guardar_imagen(self, imagen: Image.Image, nombre_archivo: str):
        try:
            self.logger.info(f"Guardando imagen en '{nombre_archivo}'.")
            imagen.save(nombre_archivo)
        except Exception as e:
            self.logger.error(f"Error al guardar la imagen '{nombre_archivo}': {e}")

    def leer_texto_ventana_activa(self):
        self.logger.info("Leyendo texto de la ventana activa.")
        try:
            ventana = pyautogui.getActiveWindow()
            if not ventana:
                self.logger.warning("No se pudo obtener la ventana activa.")
                return []
            
            region = (ventana.left, ventana.top, ventana.width, ventana.height)
            if region[2] > 0 and region[3] > 0:
                captura = pyautogui.screenshot(region=region)
                return self.leer_texto_en_pantalla(captura)
            else:
                self.logger.warning("Ventana activa con dimensiones no válidas para captura.")
                return []
        except Exception as e:
            self.logger.error(f"Error al leer el texto de la ventana activa: {e}", exc_info=True)
            return []
