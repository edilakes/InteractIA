import os
import pymongo
from dotenv import load_dotenv
import json

# Función para convertir ObjectId a string
def default_converter(o):
    if isinstance(o, pymongo.mongo_client.ObjectId):
        return str(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
COLLECTION_TO_INSPECT = "providers_config"

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

        print(f"Inspeccionando la colección '{COLLECTION_TO_INSPECT}' en la base de datos '{MONGODB_DATABASE_NAME}'...")
        
        collection = db[COLLECTION_TO_INSPECT]
        documentos = list(collection.find())
        
        if not documentos:
            print(f"No se encontraron documentos en la colección '{COLLECTION_TO_INSPECT}'.")
        else:
            print(f"\n--- Contenido de la Colección: {COLLECTION_TO_INSPECT} ---")
            for doc in documentos:
                # Usamos json.dumps para una impresión bonita y manejo de tipos de datos de Mongo
                print(json.dumps(doc, indent=4, default=str))
                print("---")
            print(f"--- Fin del Contenido ({len(documentos)} documentos) ---")

            print("\n--- Verificación de Environment Variables ---")
            for doc in documentos:
                for provider in doc.get("providers", []):
                    for key_config in provider.get("api_keys", []):
                        env_var_name = key_config.get("api_key_env_name")
                        if env_var_name:
                            env_var_value = os.getenv(env_var_name)
                            if env_var_value:
                                print(f"(+) La variable de entorno '{env_var_name}' para la clave '{key_config.get('name')}' está configurada.")
                            else:
                                print(f"(-) ADVERTENCIA: La variable de entorno '{env_var_name}' para la clave '{key_config.get('name')}' NO está configurada.")
                        else:
                            print(f"(-) ADVERTENCIA: No se encontró 'api_key_env_name' para la clave '{key_config.get('name')}'.")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")