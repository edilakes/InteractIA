import pyautogui
import time

def verificar_posicion_raton():
    """
    Imprime la posición actual del cursor del ratón cada segundo.
    """
    try:
        print("Verificando la posición del ratón. Mueve el cursor por la pantalla.")
        print("Presiona Ctrl+C en la terminal para detener el script.")
        while True:
            x, y = pyautogui.position()
            print(f"Posición actual: X={x}, Y={y}", end='\r')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nScript detenido por el usuario.")
    except Exception as e:
        print(f"\nOcurrió un error: {e}")

if __name__ == "__main__":
    verificar_posicion_raton()
