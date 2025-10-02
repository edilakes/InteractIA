import os
from dotenv import load_dotenv
import pymongo
import google.generativeai as genai

def verificar_credenciales():
    """
    Carga las credenciales desde el archivo .env y prueba las conexiones
    a MongoDB y a la API de Gemini.
    """
    print("Cargando credenciales desde el archivo .env...")
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")

    if not gemini_api_key or "SU_API_KEY" in gemini_api_key:
        print("(-) ERROR: La API Key de Gemini no se ha encontrado o no se ha modificado en el archivo .env")
    else:
        print("(+) Credencial de Gemini encontrada.")
        try:
            genai.configure(api_key=gemini_api_key)
            # Hacemos una llamada simple para verificar que la clave es válida
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if models:
                print("(+) Conexión con la API de Gemini exitosa.")
            else:
                print("(-) ERROR: La API Key de Gemini parece válida, pero no se encontraron modelos compatibles.")
        except Exception as e:
            print(f"(-) ERROR al conectar con la API de Gemini: {e}")

    print("-" * 20)

    if not mongo_uri or "SU_CADENA_DE_CONEXION" in mongo_uri:
        print("(-) ERROR: La URI de MongoDB no se ha encontrado o no se ha modificado en el archivo .env")
    else:
        print("(+) Credencial de MongoDB encontrada.")
        try:
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # El comando ping es la forma estándar de probar una conexión
            client.admin.command('ping')
            print("(+) Conexión con MongoDB exitosa.")
        except pymongo.errors.ConnectionFailure as e:
            print(f"(-) ERROR de conexión con MongoDB: {e}")
        except pymongo.errors.ConfigurationError as e:
            print(f"(-) ERROR de configuración de MongoDB (revisa la cadena de conexión): {e}")
        except Exception as e:
            print(f"(-) ERROR inesperado al conectar con MongoDB: {e}")

if __name__ == "__main__":
    verificar_credenciales()
