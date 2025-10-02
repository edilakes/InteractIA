from PIL import Image
from vision import Vision
from logger_config import setup_logging
import logging

if __name__ == '__main__':
    setup_logging()
    main_logger = logging.getLogger("InteractIA")
    main_logger.info("--- Analizando imagen con el módulo de visión ---")

    vision = Vision()
    try:
        imagen = Image.open("prueba_vision_ocr.png")
        main_logger.info("Imagen cargada exitosamente.")
        
        datos_texto = vision.leer_texto_en_pantalla(imagen)
        
        if datos_texto:
            main_logger.info("Se ha detectado el siguiente texto en la imagen:")
            for bloque in datos_texto:
                print(bloque)
        else:
            main_logger.warning("No se detectó texto en la imagen o Tesseract no está configurado correctamente.")

    except FileNotFoundError:
        main_logger.error("No se encontró el archivo 'prueba_vision_ocr.png'.")
    except Exception as e:
        main_logger.error(f"Ocurrió un error: {e}")

    main_logger.info("--- Análisis de imagen finalizado ---")
