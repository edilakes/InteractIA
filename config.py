import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Credenciales y Endpoints ---

# URI de conexión para la base de datos MongoDB
MONGO_URI = os.getenv("MONGO_URI")

# --- Configuración de la Base de Datos ---

# Nombre de la base de datos principal
MONGODB_DATABASE_NAME = "interactia_db"

# Nombre de la colección para el historial de chat
MONGODB_CHAT_COLLECTION = "chat_history"

# Nombre de la colección para la base de conocimiento
MONGODB_KB_COLLECTION = "knowledge_base"

# Nombre de la colección para las oportunidades de aprendizaje descubiertas
MONGODB_OPORTUNIDADES_COLLECTION = "oportunidades_aprendizaje"

# Nombre de la colección para registrar sesiones de chat ya analizadas
MONGODB_SESIONES_ANALIZADAS_COLLECTION = "sesiones_analizadas"

# Nombre de la colección para las configuraciones de proveedores de modelos de IA
MONGODB_PROVIDERS_COLLECTION = "providers_config"

# Número de mensajes a recuperar del historial de chat
CHAT_HISTORY_LENGTH = 20

# --- Configuraciones del Agente ---
# (La configuración del modelo de IA ahora se gestiona a través de models.json)

# --- Verificación de configuración ---

def verificar_configuracion():
    """
    Comprueba que las variables de entorno esenciales estén cargadas.
    """
    print("Verificando la configuración de la aplicación...")
    
    # La verificación de la API key del modelo se hará al cargar el proveedor específico.
    # Esto permite que diferentes modelos usen diferentes variables de entorno.

    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("(-) ADVERTENCIA: La variable de entorno MONGO_URI no está configurada.")
        return False
    else:
        print("(+) La URI de MongoDB está cargada.")
    
    print("\nConfiguración base cargada correctamente.")
    return True

if __name__ == "__main__":
    verificar_configuracion()
