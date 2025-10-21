import logging
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    """
    Formateador de logs que estructura la salida en formato JSON.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # Si hay datos extra, los añadimos al log
        if hasattr(record, 'extra_data'):
            log_record['extra_data'] = record.extra_data
        
        return json.dumps(log_record, ensure_ascii=False)

class GUIHandler(logging.Handler):
    """
    Un handler de logging que envía los registros a la GUI a través de un comunicador.
    """
    def __init__(self, comunicador):
        super().__init__()
        self.comunicador = comunicador

    def emit(self, record):
        msg = self.format(record)
        self.comunicador.log(msg)

def setup_logging(log_level=logging.DEBUG, comunicador=None):
    """
    Configura el sistema de logging para todo el proyecto.
    """
    logger = logging.getLogger("InteractIA")
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler for detailed DEBUG logs in JSON format
    file_handler = RotatingFileHandler("interactia_debug.log", maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # Ensure file handler captures DEBUG
    json_formatter = JsonFormatter()
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # Console handler for general INFO logs with a simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Console shows INFO and above
    simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # GUI handler
    if comunicador:
        gui_handler = GUIHandler(comunicador)
        gui_handler.setLevel(logging.INFO) # Only show INFO and above in the GUI
        gui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)

if __name__ == '__main__':
    # Configurar el logging
    setup_logging(log_level=logging.DEBUG)
    
    # Obtener una instancia del logger
    test_logger = logging.getLogger("InteractIA")
    
    # Ejemplos de uso
    test_logger.debug("Este es un mensaje de depuración.")
    test_logger.info("El agente ha iniciado una nueva tarea.", extra={'extra_data': {'tarea_id': 123, 'objetivo': 'test'}})
    test_logger.warning("La confianza del OCR es baja.", extra={'extra_data': {'confianza': 45}})
    try:
        x = 1 / 0
    except ZeroDivisionError:
        test_logger.error("Error al realizar una división.", exc_info=True)
    
    print("\nLogs de prueba generados en 'interactia.log'")