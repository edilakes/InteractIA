from interactia_gui import InteractIAGUI
from logger_config import setup_logging
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
    setup_logging() # Initialize logging at the very beginning
    parser = argparse.ArgumentParser(description="InteractIA - Agente de IA Autónomo")
    parser.add_argument("--supervisando-a", type=str, help="El ID de la instancia de InteractIA a supervisar.")
    # Añadir aquí futuros argumentos de línea de comandos

    args, unknown = parser.parse_known_args()

    objetivo_cli = " ".join(unknown).strip()

    # Si se proporciona un objetivo en la línea de comandos, ejecutar en modo CLI
    if objetivo_cli:
        from agente_v3 import AgenteV3
        from model_manager import get_default_provider_config, get_model_provider

        print("Ejecutando en modo CLI...")
        try:
            # Obtener la configuración del proveedor por defecto
            provider_type, key_config, model_name = get_default_provider_config()
            
            # Obtener la instancia del proveedor del modelo
            print(f"Cargando proveedor por defecto: {provider_type} con modelo {model_name}")
            model_provider = get_model_provider(provider_type, key_config)
            
            # Instanciar el nuevo agente V2
            agente = AgenteV3(
                model_provider=model_provider,
                model_name=model_name,
                callback_hablar=lambda msg: print(f"\n[AGENTE]: {msg}\n")
            )
            
            # Ejecutar el ciclo del agente
            agente.run_cycle(user_message=objetivo_cli, session_id='cli_session')

        except Exception as e:
            print(f"Error al ejecutar el agente en modo CLI: {e}")

    else:
        # De lo contrario, iniciar la GUI
        id_instancia = generar_id_aleatorio()
        titulo_ventana = f"interactia-{id_instancia}"

        root = tk.Tk()
        root.withdraw() # Hide the main window initially
        app = InteractIAGUI(root, titulo=titulo_ventana, id_objetivo=args.supervisando_a)
        root.after(0, app.start_gui) # Call start_gui after mainloop starts
        root.mainloop()
        
        # Close the MongoDB connection when the GUI mainloop exits
        try:
            provider_db_manager.close_connection()
            print("Conexión a MongoDB cerrada.")
        except Exception as e:
            print(f"Error al cerrar la conexión a MongoDB: {e}")

if __name__ == "__main__":
    main()