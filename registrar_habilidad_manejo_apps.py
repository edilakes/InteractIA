from knowledge_base import KnowledgeBase
import logging

# Configuración inicial de logging
logger = logging.getLogger(__name__)

# Definición de la habilidad IMPERATIVA (la acción)
datos_habilidad = {
    "descripcion": "Un conjunto de acciones para gestionar aplicaciones, como abrirlas o registrarlas en la base de conocimiento.",
    "tipo": "Imperativa",
    "contexto_aplicacion": ["General"],
    "modulo_implementacion": "habilidad_manejo_aplicaciones",
    "acciones": [
        {
            "nombre": "abrir_aplicacion_por_nombre",
            "descripcion": "Abre una aplicación de escritorio (ej. 'bloc de notas') usando la línea de comandos de forma visible para el usuario.",
            "parametros": [
                {"nombre": "nombre_app", "tipo": "str", "descripcion": "El nombre popular de la aplicación a abrir."}
            ],
            "ejemplo_uso": "abrir_aplicacion_por_nombre('bloc de notas')"
        },
        {
            "nombre": "registrar_nueva_aplicacion",
            "descripcion": "Enseña al agente la ubicación de una nueva aplicación para que pueda abrirla en el futuro.",
            "parametros": [
                {"nombre": "nombres_populares", "tipo": "list", "descripcion": "Lista de nombres para la app (ej. ['vscode', 'visual studio code'])"},
                {"nombre": "ruta_absoluta", "tipo": "str", "descripcion": "Ruta completa al ejecutable (ej. 'C:\\Users\\user\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe')"}
            ],
            "ejemplo_uso": "registrar_nueva_aplicacion(['vscode'], 'C:\\path\\to\\Code.exe')"
        }
    ]
}

def registrar_habilidad_accion():
    """
    Guarda la habilidad de acción para manejar aplicaciones en la KB.
    """
    kb = KnowledgeBase()
    if kb.client:
        try:
            kb.aprender_habilidad(
                nombre_recurso="accion_manejo_aplicaciones",
                tipo_recurso="Habilidad Imperativa",
                datos_habilidad=datos_habilidad
            )
            logger.info("Habilidad de acción 'accion_manejo_aplicaciones' registrada/actualizada.")
            return True
        except Exception as e:
            logger.error(f"Error al registrar la habilidad de acción: {e}", exc_info=True)
            return False
    else:
        logger.error("No se pudo conectar a la KB. No se registró la habilidad.")
        return False

if __name__ == "__main__":
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)
    
    print("Registrando las habilidades de acción para el manejo de aplicaciones...")
    if registrar_habilidad_accion():
        print("Registro de habilidades de acción completado con éxito.")
    else:
        print("Fallo en el registro de las habilidades de acción.")
