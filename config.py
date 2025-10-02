import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Credenciales y Endpoints ---

# Clave de API para el servicio de Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# URI de conexión para la base de datos MongoDB
MONGO_URI = os.getenv("MONGO_URI")

# --- Configuraciones del Agente ---

# Modelo de Gemini a utilizar para la toma de decisiones
# Es importante elegir uno que sea multimodal (acepte imágenes y texto)
GEMINI_MODEL_NAME = "models/gemini-2.5-flash"

# --- Verificación de configuración ---

def verificar_configuracion():
    """
    Comprueba que las variables de entorno esenciales estén cargadas.
    """
    print("Verificando la configuración de la aplicación...")
    
    if not GEMINI_API_KEY or "SU_API_KEY" in GEMINI_API_KEY:
        print("(-) ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada.")
        return False
    else:
        print("(+) La API Key de Gemini está cargada.")

    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("(-) ADVERTENCIA: La variable de entorno MONGO_URI no está configurada.")
        return False
    else:
        print("(+) La URI de MongoDB está cargada.")
    
    print("\nConfiguración cargada correctamente.")
    return True

if __name__ == "__main__":
    verificar_configuracion()
