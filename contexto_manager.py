import pyautogui
import logging

logger = logging.getLogger(__name__)

# Mapeo de partes de títulos de ventana a nombres de contexto normalizados
# La clave es una subcadena (en minúsculas) que se busca en el título de la ventana
# El valor es el nombre del contexto que se devolverá
MAPEO_CONTEXTO = {
    "bloc de notas": "Bloc de notas",
    "notepad": "Bloc de notas",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "visual studio code": "Visual Studio Code",
    "explorador de archivos": "Explorador de archivos",
    "file explorer": "Explorador de archivos",
}

def detectar_contexto_actual() -> str:
    """
    Identifica la aplicación actualmente en primer plano analizando el título de la ventana activa.

    Returns:
        str: El nombre del contexto de la aplicación (ej. "Microsoft Word"), 
             o "General" si no se reconoce una aplicación específica.
    """
    try:
        ventana_activa = pyautogui.getActiveWindow()
        if not ventana_activa:
            logger.warning("No se pudo obtener la ventana activa. Devolviendo contexto 'General'.")
            return "General"

        titulo_ventana = ventana_activa.title.lower()
        logger.debug(f"Ventana activa detectada: '{titulo_ventana}'")

        # Buscar en el mapeo una coincidencia
        for clave, contexto in MAPEO_CONTEXTO.items():
            if clave in titulo_ventana:
                logger.info(f"Contexto reconocido: '{contexto}' a partir del título de la ventana.")
                return contexto
        
        # Si no hay ninguna coincidencia en el mapeo, es un contexto no específico
        logger.info(f"No se reconoció un contexto específico para '{titulo_ventana}'. Devolviendo 'General'.")
        return "General"

    except Exception as e:
        logger.error(f"Error al detectar el contexto de la ventana: {e}", exc_info=True)
        return "General"

if __name__ == '__main__':
    # Prueba para verificar la detección de contexto
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)

    print("Detectando el contexto de la ventana actual en 3 segundos...")
    pyautogui.sleep(3)
    contexto = detectar_contexto_actual()
    print(f"--> Contexto detectado: {contexto}")
