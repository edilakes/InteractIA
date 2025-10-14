import os
import pymongo
from dotenv import load_dotenv
import datetime
import argparse

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
MONGODB_CHAT_COLLECTION = "chat_history"

# --- Argumentos de línea de comandos ---
parser = argparse.ArgumentParser(description="Obtener el historial de chat de una sesión de InteractIA desde MongoDB.")
parser.add_argument("--session_id", required=True, help="El ID de la sesión para la cual obtener el historial.")
args = parser.parse_args()
SESSION_KEY = args.session_id

# --- Script ---
if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
    print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
    print("Por favor, asegúrate de que MONGO_URI esté definida en tu entorno o en un archivo .env.")
else:
    try:
        print(f"Conectando a MongoDB con la URI proporcionada...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]
        print("Conexión exitosa.")

        print(f"Buscando historial de chat para la sesión: {SESSION_KEY}...")
        mensajes_cursor = collection_chats.find(
            {"session_key": SESSION_KEY}
        ).sort("timestamp", pymongo.ASCENDING)

        historial = list(mensajes_cursor)

        if not historial:
            print(f"No se encontró historial de chat para la sesión '{SESSION_KEY}'.")
        else:
            print(f"--- Historial de Chat para la sesión: {SESSION_KEY} ---")
            for msg in historial:
                role = msg.get('role', 'desconocido')
                content = msg.get('content', {}).get('texto', '(sin texto)')
                timestamp = msg.get('timestamp', 'sin fecha')
                if isinstance(timestamp, datetime.datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {role}: {content}")
            print(f"--- Fin del Historial ---")
            print(f"Se encontraron {len(historial)} mensajes.")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
        print("Verifica que la URI de conexión es correcta y que la base de datos está accesible.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")