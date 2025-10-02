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

def setup_logging(log_level=logging.INFO):
    """
    Configura el sistema de logging para todo el proyecto.
    """
    logger = logging.getLogger("InteractIA")
    logger.setLevel(log_level)

    # Evitar que se añadan manejadores duplicados si se llama a esta función varias veces
    if logger.hasHandlers():
        logger.handlers.clear()

    # Crear un manejador que rota los logs, para que no crezcan indefinidamente
    # 1MB por archivo, manteniendo 3 archivos de backup.
    handler = RotatingFileHandler("interactia.log", maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    
    # Crear el formateador JSON y añadirlo al manejador
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    
    # Añadir el manejador al logger
    logger.addHandler(handler)

    # Opcional: Añadir un manejador para la consola para ver los logs en tiempo real (con formato simple)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    # No añadir el handler de consola para no duplicar la salida que ya tenemos
    # logger.addHandler(console_handler)

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
