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

def get_latest_session_id_from_db():
    """Lee la base de datos para encontrar el último ID de sesión."""
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]

        latest_session = collection_chats.find_one(sort=[("timestamp", pymongo.DESCENDING)])
        if latest_session:
            session_id = latest_session.get("session_key")
            print(f"Último ID de sesión encontrado en la base de datos: {session_id}")
            return session_id
    except Exception as e:
        print(f"Error al leer la base de datos: {e}")
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

def get_all_logs(log_path):
    """Muestra todos los logs del archivo."""
    print(f"\n--- Logs del archivo: {log_path} ---")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                print(line.strip())
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
        session_to_find = get_latest_session_id_from_db()

    if session_to_find:
        get_chat_history(session_to_find)
        get_all_logs(LOG_FILE_PATH)
    else:
        print("No se pudo determinar un ID de sesión para continuar.")
