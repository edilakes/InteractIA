from interactia_gui import InteractIAGUI
import tkinter as tk
import sys
import threading
import random
import string
import argparse

from provider_db_manager import provider_db_manager # Import the global instance

def generar_id_aleatorio(longitud=6):
    """Genera un ID alfanumérico aleatorio."""
    caracteres = string.ascii_lowercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    """Punto de entrada principal para la aplicación InteractIA."""
    parser = argparse.ArgumentParser(description="InteractIA - Agente de IA Autónomo")
    parser.add_argument("--supervisando-a", type=str, help="El ID de la instancia de InteractIA a supervisar.")
    # Añadir aquí futuros argumentos de línea de comandos

    args, unknown = parser.parse_known_args()

    objetivo_cli = " ".join(unknown).strip()

    # Si se proporciona un objetivo en la línea de comandos, ejecutar en modo CLI
    if objetivo_cli:
        from agente import Agente
        agente = Agente(callback_hablar=lambda msg: print(f"Agente: {msg}"))
        agente.establecer_objetivo(objetivo_cli)
        agente.stream_run()
    else:
        # De lo contrario, iniciar la GUI
        id_instancia = generar_id_aleatorio()
        titulo_ventana = f"interactia-{id_instancia}"

        root = tk.Tk()
        app = InteractIAGUI(root, titulo=titulo_ventana, id_objetivo=args.supervisando_a)
        root.mainloop()
        
        # Close the MongoDB connection when the GUI mainloop exits
        try:
            provider_db_manager.close_connection()
            print("Conexión a MongoDB cerrada.")
        except Exception as e:
            print(f"Error al cerrar la conexión a MongoDB: {e}")

if __name__ == "__main__":
    main()