from knowledge_base import KnowledgeBase
import logging

# Configuración inicial de logging
logger = logging.getLogger(__name__)

# Definición de la habilidad: Navegación por menús con Alt
datos_habilidad = {
    "descripcion": "Una habilidad para navegar por los menús de una aplicación de escritorio. Activa la barra de menús con la tecla Alt, detecta la letra de atajo subrayada de una opción de menú específica y la selecciona.",
    "tipo": "Imperativa", # Indica que es una habilidad ejecutable
    "contexto_aplicacion": ["General"], # Habilidad disponible en cualquier contexto
    "acciones": [
        {
            "nombre": "navegar_menu_con_alt",
            "descripcion": "Busca y selecciona una opción de menú principal (ej. 'Archivo', 'Editar') detectando su atajo de teclado (letra subrayada) después de presionar Alt.",
            "parametros": [
                {"nombre": "texto_menu", "tipo": "str", "descripcion": "El texto visible de la opción del menú que se desea abrir."}
            ],
            "ejemplo_uso": "navegar_menu_con_alt('Archivo')"
        }
    ],
    "modulo_implementacion": "habilidad_navegacion_menus",
    "funcion_principal": "navegar_menu_con_alt",
    "dependencias": ["controlador.py", "vision.py"],
    "heuristicas": [
        "Usar cuando se necesita acceder a funcionalidades que no tienen un atajo de teclado directo.",
        "Especialmente útil en aplicaciones de escritorio tradicionales con una barra de menú estándar (File, Edit, View, etc.).",
        "Asegurarse de que la ventana de la aplicación objetivo esté en primer plano antes de usar."
    ]
}

def registrar_habilidad():
    """
    Guarda la habilidad de navegación por menús en la base de conocimiento.
    """
    kb = KnowledgeBase()
    if kb.client:
        try:
            kb.aprender_habilidad(
                nombre_recurso="navegacion_menus_alt",
                tipo_recurso="Interacción GUI",
                datos_habilidad=datos_habilidad
            )
            logger.info("Habilidad 'navegacion_menus_alt' registrada/actualizada en la base de conocimiento.")
            return True
        except Exception as e:
            logger.error(f"Error al registrar la habilidad: {e}", exc_info=True)
            return False
    else:
        logger.error("No se pudo conectar a la base de conocimiento (MongoDB). No se registró la habilidad.")
        return False

if __name__ == "__main__":
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)
    
    print("Registrando la habilidad de navegación por menús...")
    if registrar_habilidad():
        print("Registro completado con éxito.")
    else:
        print("Fallo en el registro de la habilidad.")