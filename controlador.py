import pyautogui
import time
import os
import logging

class Controlador:
    """
    Clase que abstrae el control del ratón, teclado y pantalla a través de pyautogui.
    Contiene únicamente acciones primitivas que son wrappers directos de pyautogui.
    """
    def __init__(self):
        """
        Inicializa el controlador y desactiva el fail-safe de pyautogui.
        """
        self.logger = logging.getLogger("InteractIA")
        pyautogui.FAILSAFE = False
        self.logger.debug("Controlador inicializado.")

    def enfocar_ventana(self, titulo: str) -> bool:
        """Encuentra una ventana por su título y la activa (la trae al frente)."""
        try:
            ventanas = pyautogui.getWindowsWithTitle(titulo)
            if ventanas:
                ventana = ventanas[0]
                ventana.activate()
                self.logger.info(f"Ventana '{titulo}' enfocada correctamente.")
                return True
            else:
                self.logger.warning(f"No se encontró ninguna ventana con el título: '{titulo}'")
                return False
        except Exception as e:
            self.logger.error(f"Error al enfocar la ventana '{titulo}': {e}")
            return False

    def mover_raton(self, x, y, duracion=1):
        self.logger.info(f"Moviendo ratón a ({x}, {y}).")
        pyautogui.moveTo(x, y, duration=duracion)

    def obtener_posicion_raton(self):
        pos = pyautogui.position()
        self.logger.debug(f"Posición del ratón obtenida: {pos}")
        return pos

    def escribir(self, texto, intervalo=0.05):
        self.logger.info(f"Escribiendo texto de longitud {len(texto)}.")
        pyautogui.write(texto, interval=intervalo)

    def capturar_pantalla(self, nombre_archivo="captura_pantalla.png"):
        self.logger.info(f"Capturando pantalla y guardando como '{nombre_archivo}'.")
        pyautogui.screenshot(nombre_archivo)
        return nombre_archivo

    def esperar(self, segundos):
        self.logger.info(f"Esperando {segundos} segundos.")
        time.sleep(segundos)

    def clic(self, x=None, y=None, boton='left'):
        self.logger.info(f"Haciendo clic con botón {boton} en ({x}, {y}).")
        pyautogui.click(x, y, button=boton)

    def presionar_tecla(self, tecla):
        self.logger.info(f"Presionando tecla: '{tecla}'.")
        if '+' in tecla:
            partes = tecla.split('+')
            pyautogui.hotkey(*partes)
        else:
            pyautogui.press(tecla)

    def mantener_tecla(self, tecla):
        self.logger.info(f"Manteniendo pulsada la tecla: '{tecla}'.")
        pyautogui.keyDown(tecla)

    def soltar_tecla(self, tecla):
        self.logger.info(f"Soltando la tecla: '{tecla}'.")
        pyautogui.keyUp(tecla)

    def scroll(self, clics):
        self.logger.info(f"Haciendo scroll ({clics} clics). Positivo es arriba, negativo es abajo.")
        pyautogui.scroll(clics)

    def mouse_down(self, boton='left'):
        self.logger.info(f"Manteniendo presionado el botón del ratón: '{boton}'.")
        pyautogui.mouseDown(button=boton)

    def mouse_up(self, boton='left'):
        self.logger.info(f"Soltando el botón del ratón: '{boton}'.")
        pyautogui.mouseUp(button=boton)

    def arrastrar_a(self, x, y, duracion=1.0):
        self.logger.info(f"Arrastrando el ratón a ({x}, {y}).")
        pyautogui.dragTo(x, y, duration=duracion)

if __name__ == '__main__':
    # Para probar este módulo de forma aislada, necesitamos configurar el logger
    from logger_config import setup_logging
    setup_logging()
    main_logger = logging.getLogger("InteractIA")

    main_logger.info("--- Iniciando prueba del Controlador --- ")
    controlador = Controlador()

    controlador.esperar(2)
    controlador.escribir("Prueba de logging en el controlador.")
    controlador.esperar(1)
    controlador.mover_raton(300, 300)
    controlador.capturar_pantalla("prueba_controlador_log.png")

    main_logger.info("--- Prueba del Controlador finalizada --- ")
