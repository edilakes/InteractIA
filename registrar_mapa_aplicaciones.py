from knowledge_base import KnowledgeBase
import logging

# Configuración inicial de logging
logger = logging.getLogger(__name__)

# Definición del mapa de aplicaciones conocido
# Este es el componente de CONOCIMIENTO
datos_mapa = {
    "descripcion": "Un registro de aplicaciones conocidas, sus nombres populares y la ruta a sus ejecutables.",
    "contexto_aplicacion": ["General"], # Este conocimiento es de propósito general
    "aplicaciones": [
        {
            "nombres_populares": ["bloc de notas", "notepad"],
            "ejecutable": "notepad.exe",
            "ruta_absoluta": "C:\\Windows\\System32\\notepad.exe"
        }
        # Se pueden añadir más aplicaciones aquí en el futuro
    ]
}

def registrar_mapa():
    """
    Guarda el mapa de aplicaciones en la base de conocimiento.
    """
    kb = KnowledgeBase()
    if kb.client:
        try:
            kb.aprender_habilidad(
                nombre_recurso="registro_ejecutables_windows",
                tipo_recurso="Mapa de Conocimiento",
                datos_habilidad=datos_mapa
            )
            logger.info("Mapa de aplicaciones 'registro_ejecutables_windows' registrado/actualizado en la KB.")
            return True
        except Exception as e:
            logger.error(f"Error al registrar el mapa de aplicaciones: {e}", exc_info=True)
            return False
    else:
        logger.error("No se pudo conectar a la KB. No se registró el mapa de aplicaciones.")
        return False

if __name__ == "__main__":
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)
    
    print("Registrando el mapa de conocimiento de aplicaciones...")
    if registrar_mapa():
        print("Registro del mapa completado con éxito.")
    else:
        print("Fallo en el registro del mapa.")
