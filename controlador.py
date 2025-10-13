import pyautogui
import time
import os
import logging

class Controlador:
    """
    Clase que abstrae el control del ratón, teclado y pantalla a través de pyautogui.
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
        self.logger.info(f"Moviendo ratón a ({x}, {y}).", extra={'extra_data': {'x': x, 'y': y, 'duracion': duracion}})
        pyautogui.moveTo(x, y, duration=duracion)

    def obtener_posicion_raton(self):
        pos = pyautogui.position()
        self.logger.debug(f"Posición del ratón obtenida: {pos}")
        return pos

    def escribir(self, texto, intervalo=0.05):
        # No loguear el texto completo por si es información sensible
        self.logger.info("Escribiendo texto.", extra={'extra_data': {'longitud': len(texto), 'intervalo': intervalo}})
        pyautogui.write(texto, interval=intervalo)

    def capturar_pantalla(self, nombre_archivo="captura_pantalla.png"):
        self.logger.info(f"Capturando pantalla y guardando como '{nombre_archivo}'.", extra={'extra_data': {'archivo': nombre_archivo}})
        pyautogui.screenshot(nombre_archivo)
        return nombre_archivo

    def esperar(self, segundos):
        self.logger.info(f"Esperando {segundos} segundos.", extra={'extra_data': {'segundos': segundos}})
        time.sleep(segundos)

    def clic(self, x=None, y=None, boton='left'):
        self.logger.info(f"Haciendo clic con botón {boton}.", extra={'extra_data': {'x': x, 'y': y, 'boton': boton}})
        pyautogui.click(x, y, button=boton)

    def presionar_tecla(self, tecla):
        self.logger.info(f"Presionando tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        pyautogui.press(tecla)

    def mantener_tecla(self, tecla):
        self.logger.info(f"Manteniendo pulsada la tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        pyautogui.keyDown(tecla)

    def soltar_tecla(self, tecla):
        self.logger.info(f"Soltando la tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        pyautogui.keyUp(tecla)

    def scroll(self, direccion, clics):
        self.logger.info(f"Haciendo scroll hacia {direccion} ({clics} clics).", extra={'extra_data': {'direccion': direccion, 'clics': clics}})
        # pyautogui.scroll() toma un valor positivo para 'arriba' y negativo para 'abajo'
        if direccion == 'arriba':
            pyautogui.scroll(clics)
        elif direccion == 'abajo':
            pyautogui.scroll(-clics)

    def arrastrar_barra(self, direccion, porcentaje):
        self.logger.info(f"Arrastrando barra de scroll hacia {direccion} un {porcentaje}%.")
        
        # Obtener el tamaño de la ventana activa
        ventana = pyautogui.getActiveWindow()
        if not ventana:
            self.logger.warning("No se pudo obtener la ventana activa para arrastrar la barra.")
            return

        # Asumir que la barra de scroll vertical está a la derecha
        # y la horizontal abajo.
        if direccion == "vertical":
            # Punto de inicio del arrastre (borde derecho, a un 25% de la altura para empezar)
            x_inicio = ventana.left + ventana.width - 15 # Un poco a la izquierda del borde
            y_inicio = ventana.top + ventana.height * 0.25
            
            # Punto final del arrastre
            x_fin = x_inicio
            # La distancia a mover es un porcentaje de la altura total de la ventana
            distancia = ventana.height * (porcentaje / 100)
            y_fin = y_inicio + distancia

            # Realizar el arrastre
            pyautogui.moveTo(x_inicio, y_inicio)
            pyautogui.dragTo(x_fin, y_fin, duration=1.0, button='left')

        elif direccion == "horizontal":
            # Punto de inicio del arrastre (borde inferior, a un 25% del ancho)
            x_inicio = ventana.left + ventana.width * 0.25
            y_inicio = ventana.top + ventana.height - 15 # Un poco arriba del borde
            
            # Punto final del arrastre
            distancia = ventana.width * (porcentaje / 100)
            x_fin = x_inicio + distancia
            y_fin = y_inicio

            # Realizar el arrastre
            pyautogui.moveTo(x_inicio, y_inicio)
            pyautogui.dragTo(x_fin, y_fin, duration=1.0, button='left')
        
        self.logger.info("Arrastre de barra de scroll completado.")

if __name__ == '__main__':
    # Para probar este módulo de forma aislada, necesitamos configurar el logger
    from logger_config import setup_logging
    setup_logging()
    main_logger = logging.getLogger("InteractIA")

    main_logger.info("--- Iniciando prueba del Controlador --- ")
    controlador = Controlador()

    # controlador.abrir_aplicacion('notepad.exe') # This is now deprecated
    controlador.esperar(2)
    controlador.escribir("Prueba de logging en el controlador.")
    controlador.esperar(1)
    controlador.mover_raton(300, 300)
    controlador.capturar_pantalla("prueba_controlador_log.png")

    main_logger.info("--- Prueba del Controlador finalizada --- ")