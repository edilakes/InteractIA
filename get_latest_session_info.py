import os
import re
import pymongo
from dotenv import load_dotenv
import datetime
import argparse
import json

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ---
# Configuración
# ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
MONGODB_CHAT_COLLECTION = "chat_history"
LOG_FILE_PATH = "interactia_debug.log"

# ---
# Funciones
# ---

def get_latest_session_id_from_log(log_path):
    """Lee el archivo de log desde el final para encontrar el último ID de sesión."""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Buscar el ID de sesión desde la última línea hacia atrás
        for line in reversed(lines):
            match = re.search(r'interactia-([a-zA-Z0-9]+)', line)
            if match:
                session_id = match.group(0)
                print(f"Último ID de sesión encontrado: {session_id}")
                return session_id
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de log en '{log_path}'")
    except Exception as e:
        print(f"Error al leer el archivo de log: {e}")
    return None

def get_chat_history(session_id):
    """Recupera y muestra el historial de chat para un ID de sesión dado."""
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]

        mensajes_cursor = collection_chats.find(
            {"session_key": session_id}
        ).sort("timestamp", pymongo.ASCENDING)

        historial = list(mensajes_cursor)

        if not historial:
            print(f"No se encontró historial de chat para la sesión '{session_id}'.")
        else:
            print(f"\n--- Historial de Chat para la sesión: {session_id} ---")
            for msg in historial:
                role = msg.get('role', 'desconocido')
                content = msg.get('content', {}).get('texto', '(sin texto)')
                timestamp = msg.get('timestamp', 'sin fecha')
                if isinstance(timestamp, datetime.datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {role}: {content}")
            print(f"--- Fin del Historial ---")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado al obtener el chat: {e}")

def get_session_logs(session_id, log_path):
    """Filtra y muestra los logs para un ID de sesión específico."""
    print(f"\n--- Logs para la sesión: {session_id} ---")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if session_id in line:
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            log_json = json.loads(line)
                            print(f"[{log_json.get('timestamp')}] [{log_json.get('level')}] [{log_json.get('module')}:{log_json.get('function')}:{log_json.get('line')}] {log_json.get('message')}")
                        except json.JSONDecodeError:
                            print(f"[RAW] {line}")
                    else:
                        print(f"[RAW] {line}")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de log en '{log_path}'")
    except Exception as e:
        print(f"Error al leer los logs de la sesión: {e}")
    print(f"--- Fin de los Logs ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtener información de la última sesión de depuración de InteractIA.")
    parser.add_argument("--session_id", help="ID de sesión específico a buscar. Si no se provee, se busca el último en el log.")
    args = parser.parse_args()

    session_to_find = args.session_id
    
    if not session_to_find:
        session_to_find = get_latest_session_id_from_log(LOG_FILE_PATH)

    if session_to_find:
        get_chat_history(session_to_find)
        get_session_logs(session_to_find, LOG_FILE_PATH)
    else:
        print("No se pudo determinar un ID de sesión para continuar.")
