from interactia_gui import InteractIAGUI
import tkinter as tk
import sys
import threading
import random
import string
import argparse

def generar_id_aleatorio(longitud=6):
    """Genera un ID alfanumérico aleatorio."""
    caracteres = string.ascii_lowercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    """Punto de entrada principal para la aplicación InteractIA."""
    parser = argparse.ArgumentParser(description="InteractIA - Agente de IA Autónomo")
    parser.add_argument("--controlar-id", type=str, help="El ID de la instancia de InteractIA a controlar.")
    # Añadir aquí futuros argumentos de línea de comandos

    args, unknown = parser.parse_known_args()

    # Si se ejecuta con un objetivo desde la línea de comandos (sin GUI)
    if unknown:
        from agente import Agente
        # Este modo no tiene ID de ventana propio ni objetivo por ahora
        agente = Agente(callback_hablar=lambda msg: print(f"Agente: {msg}"))
        objetivo = " ".join(unknown)
        agente.establecer_objetivo(objetivo)
        agente.run()
    else:
        # Modo GUI
        id_instancia = generar_id_aleatorio()
        titulo_ventana = f"interactia-{id_instancia}"

        root = tk.Tk()
        app = InteractIAGUI(root, titulo=titulo_ventana, id_objetivo=args.controlar_id)
        root.mainloop()

if __name__ == "__main__":
    main()
