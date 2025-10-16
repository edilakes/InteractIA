import logging
import re
from controlador import Controlador
from vision import Vision
from knowledge_base import KnowledgeBase
from contexto_manager import detectar_contexto_actual

logger = logging.getLogger(__name__)

def abrir_aplicacion_por_nombre(nombre_app: str) -> bool:
    """
    Abre una aplicación buscándola en la base de conocimiento y ejecutándola 
    a través de la línea de comandos, simulando la interacción humana.

    Args:
        nombre_app (str): El nombre popular de la aplicación a abrir (ej. "bloc de notas").

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario.
    """
    logger.info(f"Iniciando habilidad para abrir la aplicación: '{nombre_app}'")
    kb = KnowledgeBase()
    controlador = Controlador()

    # 1. Consultar la base de conocimiento para encontrar la ruta
    mapa_apps = kb.conocer_habilidad("registro_ejecutables_windows")
    ruta_ejecutable = None

    if mapa_apps:
        nombre_app_lower = nombre_app.lower()
        for app in mapa_apps.get("datos", {}).get("aplicaciones", []):
            if nombre_app_lower in [n.lower() for n in app["nombres_populares"]]:
                ruta_ejecutable = app["ruta_absoluta"]
                logger.info(f"Ruta encontrada en la KB para '{nombre_app}': {ruta_ejecutable}")
                break
    
    if not ruta_ejecutable:
        logger.warning(f"No se encontró una ruta en la KB para '{nombre_app}'. Intentando ejecución directa.")
        # Como fallback, usamos el propio nombre de la app como ejecutable (ej. 'notepad.exe')
        # y esperamos que esté en el PATH del sistema.
        if not nombre_app.endswith(".exe"):
             logger.warning(f"El nombre '{nombre_app}' no parece un ejecutable. La ejecución puede fallar.")
        ruta_ejecutable = nombre_app

    # 2. Abrir el Símbolo del Sistema vía GUI
    logger.info("Abriendo el Símbolo del Sistema vía Win+R...")
    controlador.presionar_tecla("win+r")
    controlador.esperar(0.5)
    # Aquí se podría añadir una verificación de que la ventana "Ejecutar" apareció
    controlador.escribir("cmd.exe")
    controlador.presionar_tecla("enter")
    controlador.esperar(1) # Esperar a que la ventana de cmd se abra

    # 3. Verificar que la ventana de cmd está activa
    contexto = detectar_contexto_actual()
    if contexto not in ["Símbolo del sistema", "Command Prompt"]:
        logger.error(f"No se pudo verificar que el Símbolo del Sistema esté activo. Contexto detectado: {contexto}")
        # Intentar cerrar la ventana que se haya abierto por error
        controlador.presionar_tecla("alt+f4")
        return False
    
    logger.info("Símbolo del Sistema verificado. Escribiendo comando para lanzar la aplicación.")

    # 4. Escribir y ejecutar el comando para lanzar la app
    # Usamos start "" para manejar correctamente rutas con espacios y no bloquear el cmd
    comando = f'start "" "{ruta_ejecutable}"\n' # Se añade \n para simular Enter
    controlador.escribir(comando)
    controlador.esperar(2) # Esperar a que la aplicación se lance

    # 5. Cerrar la ventana de cmd
    logger.info("Cerrando el Símbolo del Sistema.")
    controlador.escribir("exit\n")
    
    return True

def registrar_nueva_aplicacion(nombres_populares: list, ruta_absoluta: str) -> bool:
    """
    Añade una nueva aplicación al mapa de conocimiento del agente.

    Args:
        nombres_populares (list): Lista de nombres con los que se conoce a la app.
        ruta_absoluta (str): Ruta completa al archivo .exe de la aplicación.

    Returns:
        bool: True si se registró correctamente, False en caso contrario.
    """
    logger.info(f"Registrando nueva aplicación: {nombres_populares[0]} en '{ruta_absoluta}'")
    kb = KnowledgeBase()
    if not kb.client:
        return False

    # 1. Extraer el nombre del ejecutable de la ruta
    nombre_ejecutable = re.split(r'[\\/]', ruta_absoluta)[-1]

    # 2. Cargar el mapa de conocimiento actual
    mapa_actual = kb.conocer_habilidad("registro_ejecutables_windows")
    if not mapa_actual:
        logger.error("No se pudo cargar el mapa de aplicaciones 'registro_ejecutables_windows' de la KB.")
        return False

    # 3. Añadir la nueva aplicación (evitando duplicados por ruta)
    apps = mapa_actual.get("datos", {}).get("aplicaciones", [])
    if any(app['ruta_absoluta'] == ruta_absoluta for app in apps):
        logger.warning(f"La aplicación en la ruta '{ruta_absoluta}' ya está registrada.")
        return True # Consideramos éxito si ya existe

    apps.append({
        "nombres_populares": nombres_populares,
        "ejecutable": nombre_ejecutable,
        "ruta_absoluta": ruta_absoluta
    })
    
    mapa_actual["datos"]["aplicaciones"] = apps

    # 4. Guardar el mapa actualizado
    resultado = kb.aprender_habilidad(
        nombre_recurso="registro_ejecutables_windows",
        tipo_recurso=mapa_actual["tipo_recurso"],
        datos_habilidad=mapa_actual["datos"]
    )

    return resultado is not None

if __name__ == '__main__':
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)

    print("--- Probando habilidad de manejo de aplicaciones ---")
    print("Probando apertura de 'bloc de notas' en 3 segundos...")
    abrir_aplicacion_por_nombre("bloc de notas")

    # Prueba de registro (simulada)
    # print("\nProbando registrar una nueva aplicación...")
    # registrar_nueva_aplicacion(["MiApp", "TestApp"], "C:\\Test\\MiApp.exe")
