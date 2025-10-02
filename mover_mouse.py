import pyautogui
import time

# Desactivamos el fail-safe, ya que es necesario para la ejecucin desatendida
# donde el estado del cursor puede ser impredecible durante la desconexin.
pyautogui.FAILSAFE = False

def mover_y_capturar():
    """
    Mueve el ratón, espera un momento y luego toma una captura de pantalla como prueba.
    """
    try:
        # Damos unos segundos para que el script se inicie despus de la desconexin
        print("Iniciando en 5 segundos...")
        time.sleep(5)

        # Mover el ratón a una posición visible
        x, y = 500, 500
        print(f"Moviendo el ratón a ({x}, {y}).")
        pyautogui.moveTo(x, y, duration=2)

        # Esperar un segundo para asegurar que el movimiento se complete
        time.sleep(1)

        # Tomar la captura de pantalla como prueba
        nombre_archivo = "prueba_movimiento.png"
        print(f"Tomando captura de pantalla y guardando como '{nombre_archivo}'.")
        pyautogui.screenshot(nombre_archivo)

        print("¡Operación completada! Puedes reconectarte para verificar el archivo.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    mover_y_capturar()
