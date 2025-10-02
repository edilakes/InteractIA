import pyautogui
import time
import subprocess

# Desactivamos el fail-safe para la ejecucin desatendida
pyautogui.FAILSAFE = False

def automatizar_notepad():
    """
    Abre el Bloc de notas, escribe un mensaje y toma una captura de pantalla.
    """
    try:
        print("Iniciando en 5 segundos...")
        time.sleep(5)

        # 1. Abrir el Bloc de notas
        print("Abriendo el Bloc de notas...")
        subprocess.Popen(['notepad.exe'])

        # Esperar a que la ventana del Bloc de notas aparezca y est activa
        time.sleep(2)

        # 2. Escribir en el Bloc de notas
        mensaje = "Hola, mundo! El agente de IA est funcionando."
        print(f"Escribiendo el mensaje: '{mensaje}'")
        pyautogui.write(mensaje, interval=0.05) # El intervalo hace que la escritura sea ms natural

        # Esperar un segundo
        time.sleep(1)

        # 3. Tomar la captura de pantalla como prueba
        nombre_archivo = "prueba_notepad.png"
        print(f"Tomando captura de pantalla y guardando como '{nombre_archivo}'.")
        pyautogui.screenshot(nombre_archivo)

        print("¡Automatización de Notepad completada!")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    automatizar_notepad()
