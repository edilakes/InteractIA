import os
import pymongo
from dotenv import load_dotenv
import json

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
COLLECTION_TO_INSPECT = "habilidades"
SKILL_TO_INSPECT = "habilidades_fundamentales_agente"

# --- Script ---
if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
    print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
else:
    try:
        print(f"Conectando a MongoDB...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        print("Conexión exitosa.")

        print(f"Inspeccionando el documento '{SKILL_TO_INSPECT}' en la colección '{COLLECTION_TO_INSPECT}'...")
        
        collection = db[COLLECTION_TO_INSPECT]
        documento = collection.find_one({"nombre_recurso": SKILL_TO_INSPECT})
        
        if not documento:
            print(f"No se encontró el documento '{SKILL_TO_INSPECT}'.")
        else:
            print(f"\n--- Contenido del Documento: {SKILL_TO_INSPECT} ---")
            print(json.dumps(documento, indent=4, default=str))
            print("--- Fin del Documento ---")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
