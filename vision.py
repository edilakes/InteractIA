import pyautogui
from PIL import Image
import logging
import pytesseract
import subprocess

def buscar_tesseract():
    """
    Busca el ejecutable de Tesseract en las rutas de instalación más comunes.
    Devuelve la ruta completa si lo encuentra, de lo contrario None.
    """
    print("Buscando Tesseract OCR...")
    comandos = [
        'dir "C:\\Program Files\\Tesseract-OCR\\tesseract.exe" /s /b',
        'dir "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe" /s /b'
    ]

    for cmd in comandos:
        try:
            print(f"Ejecutando: {cmd}")
            resultado = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
            if resultado and resultado.endswith("tesseract.exe"):
                print(f"(+) Tesseract encontrado en: {resultado}")
                return resultado
        except subprocess.CalledProcessError:
            # El comando falla si no encuentra el archivo, lo cual es esperado.
            continue
        except Exception as e:
            print(f"(-) Ocurrió un error inesperado al ejecutar el comando: {e}")
            continue
            
    print("(-) Tesseract no se encontró en las rutas de instalación comunes.")
    return None

class Vision:
    """
    Clase encargada de la percepción del entorno, incluyendo captura de pantalla y OCR.
    """
    def __init__(self):
        self.logger = logging.getLogger("InteractIA")
        try:
            tesseract_path = buscar_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.logger.info(f"Usando Tesseract desde la ruta: {tesseract_path}")
            else:
                self.logger.warning("Tesseract no encontrado. El OCR no estará disponible.")
        except Exception as e:
            self.logger.error(f"Error al configurar Pytesseract. Asegúrate de que Tesseract está instalado. Error: {e}", exc_info=True)

    def capturar_pantalla(self, titulo_ventana=None):
        self.logger.debug("Capturando pantalla.")
        captura_completa = pyautogui.screenshot()
        captura_ventana = None

        if titulo_ventana:
            try:
                ventanas = pyautogui.getWindowsWithTitle(titulo_ventana)
                if ventanas:
                    ventana = ventanas[0]
                    captura_ventana = pyautogui.screenshot(region=(ventana.left, ventana.top, ventana.width, ventana.height))
                    self.logger.info(f"Capturada la ventana: '{titulo_ventana}'")
                else:
                    self.logger.warning(f"No se encontró ninguna ventana con el título: '{titulo_ventana}'")
            except Exception as e:
                self.logger.error(f"Error al capturar la ventana '{titulo_ventana}': {e}")

        return captura_completa, captura_ventana

    def guardar_imagen(self, imagen: Image.Image, nombre_archivo: str):
        self.logger.info(f"Guardando imagen en '{nombre_archivo}'.", extra={'extra_data': {'archivo': nombre_archivo}})
        imagen.save(nombre_archivo)

    def leer_texto_en_pantalla(self, imagen: Image.Image):
        """
        Utiliza OCR para extraer texto y sus coordenadas de una imagen.

        Args:
            imagen (PIL.Image.Image): La imagen de la que extraer el texto.

        Returns:
            list: Una lista de diccionarios, donde cada uno representa un bloque de texto detectado.
        """
        self.logger.info("Realizando OCR para leer texto en la imagen.")
        try:
            # Usamos image_to_data para obtener texto, coordenadas y confianza
            data = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT)
            
            bloques = []
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                # Filtramos los resultados con una confianza mínima (ej. 60%)
                confianza = int(data['conf'][i])
                if confianza > 60:
                    texto = data['text'][i].strip()
                    if texto: # Nos aseguramos de que no sea solo espacio en blanco
                        bloque = {
                            'texto': texto,
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': confianza
                        }
                        bloques.append(bloque)
            
            self.logger.info(f"OCR completado. Se encontraron {len(bloques)} bloques de texto con confianza > 60%.")
            return bloques
        except pytesseract.TesseractNotFoundError:
            self.logger.error("Tesseract no encontrado. Asegúrate de que está instalado y la ruta es correcta.", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Ocurrió un error durante el OCR: {e}", exc_info=True)
            return []

    def leer_texto_ventana_activa(self):
        """
        Captura la ventana activa y extrae el texto de ella.

        Returns:
            list: Una lista de diccionarios con el texto extraído.
        """
        self.logger.info("Leyendo texto de la ventana activa.")
        try:
            ventana = pyautogui.getActiveWindow()
            if not ventana:
                self.logger.warning("No se pudo obtener la ventana activa.")
                return []
            
            captura = pyautogui.screenshot(region=(ventana.left, ventana.top, ventana.width, ventana.height))
            return self.leer_texto_en_pantalla(captura)
        except Exception as e:
            self.logger.error(f"Error al leer el texto de la ventana activa: {e}", exc_info=True)
            return []

if __name__ == '__main__':
    from logger_config import setup_logging
    setup_logging(log_level=logging.DEBUG)
    main_logger = logging.getLogger("InteractIA")

    main_logger.info("--- Iniciando prueba del Módulo de Visión con OCR ---")
    vision = Vision()

    # 1. Capturar la pantalla
    captura_completa, captura_ventana = vision.capturar_pantalla("Explorador de archivos")
    if captura_completa:
        vision.guardar_imagen(captura_completa, "prueba_vision_completa.png")
    if captura_ventana:
        vision.guardar_imagen(captura_ventana, "prueba_vision_ventana.png")

    # 2. Leer el texto de la pantalla
    if captura_ventana:
        datos_texto = vision.leer_texto_en_pantalla(captura_ventana)
        if datos_texto:
            main_logger.info("Se ha detectado el siguiente texto en la ventana (primeros 5 bloques):")
            for bloque in datos_texto[:5]:
                # Usamos pprint para una mejor visualización del diccionario
                import pprint
                pprint.pprint(bloque)
        else:
            main_logger.warning("No se detectó texto en la ventana o Tesseract no está configurado correctamente.")

    main_logger.info("--- Prueba de Visión finalizada ---")
