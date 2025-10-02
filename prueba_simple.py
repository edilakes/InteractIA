import pyautogui

print("Intentando un movimiento simple del ratón...")

# Como medida de diagnóstico, desactivamos el fail-safe de PyAutoGUI.
# Esto evita que PyAutoGUI detenga el script si el ratón va a una esquina.
pyautogui.FAILSAFE = False

try:
    # Un intento de movimiento directo y simple.
    pyautogui.moveTo(500, 500, duration=2)
    print("El comando moveTo() se ha ejecutado sin errores.")
except Exception as e:
    print(f"Ocurrió un error durante el moveTo: {e}")
