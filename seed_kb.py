# seed_kb.py
"""
Script para poblar la Base de Conocimiento (KB) con la documentación de PyAutoGUI.
"""
import os
import sys
import logging
import pymongo
import requests
from bs4 import BeautifulSoup

# Añadir el directorio raíz al path para poder importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_KB_COLLECTION
from model_manager import get_model_provider

# URL de la documentación oficial de PyAutoGUI
PYAUTOGUI_DOCS_URL = "https://pyautogui.readthedocs.io/en/latest/"

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_mongodb_collection():
    """Establece la conexión con MongoDB y devuelve la colección de la KB."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        client.admin.command('ping') # Verificar conexión
        db = client[MONGODB_DATABASE_NAME]
        logging.info(f"Conectado a MongoDB. Base de datos: '{MONGODB_DATABASE_NAME}'")
        return db[MONGODB_KB_COLLECTION]
    except Exception as e:
        logging.error(f"Error al conectar con MongoDB: {e}")
        return None

def fetch_documentation_content():
    """Obtiene el contenido HTML de la página de documentación."""
    logging.info(f"Obteniendo contenido de: {PYAUTOGUI_DOCS_URL}")
    try:
        response = requests.get(PYAUTOGUI_DOCS_URL)
        response.raise_for_status()  # Lanza un error para códigos de estado HTTP 4xx/5xx
        logging.info("Contenido descargado con éxito.")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al descargar la documentación: {e}")
        return None

def chunk_content(html_content):
    """Divide el contenido HTML en fragmentos de texto significativos (chunks)."""
    logging.info("Procesando y dividiendo el contenido en chunks...")
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    main_content = soup.find('div', role='main')
    
    if not main_content:
        logging.warning("No se encontró el div de contenido principal (role='main'). Se usará todo el body.")
        main_content = soup.body

    chunks = []
    current_chunk = ""

    for element in main_content.find_all(['h1', 'h2', 'h3', 'p', 'pre', 'li']):
        text = element.get_text(strip=True)
        if not text:
            continue

        if element.name in ['h1', 'h2', 'h3'] and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = text + "\n"
        else:
            current_chunk += text + "\n"
        
        if len(current_chunk) > 1500:
            chunks.append(current_chunk.strip())
            current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk.strip())

    logging.info(f"Se han creado {len(chunks)} chunks de texto.")
    return chunks

def generate_embeddings(text_chunks):
    """Genera vectores de embedding para cada chunk de texto."""
    logging.info(f"Generando embeddings para {len(text_chunks)} chunks de texto...")
    try:
        provider = get_model_provider()
        logging.info(f"Usando el proveedor '{provider.provider_type}' para generar embeddings.")
    except Exception as e:
        logging.error(f"Error al obtener el proveedor de modelos: {e}")
        return None

    embedded_chunks = []
    for i, chunk in enumerate(text_chunks):
        logging.info(f"Generando embedding para el chunk {i+1}/{len(text_chunks)}...")
        embedding = provider.embed_content(chunk)
        if embedding:
            embedded_chunks.append({"text": chunk, "embedding": embedding})
        else:
            logging.warning(f"No se pudo generar el embedding para el chunk {i+1}. Se omitirá.")
    
    logging.info(f"Se generaron embeddings para {len(embedded_chunks)} chunks.")
    return embedded_chunks

def store_in_mongodb(collection, embedded_chunks):
    """Almacena los chunks con sus embeddings en MongoDB."""
    if not embedded_chunks:
        logging.warning("No hay documentos para almacenar.")
        return

    logging.info(f"Almacenando {len(embedded_chunks)} documentos en la colección '{collection.name}'...")
    try:
        # Borrar la colección existente para asegurar que los datos estén frescos
        logging.info("Borrando la colección existente para una nueva ingesta...")
        collection.delete_many({})

        # Insertar los nuevos documentos
        collection.insert_many(embedded_chunks)
        logging.info(f"Se han insertado {len(embedded_chunks)} documentos con éxito.")

    except Exception as e:
        logging.error(f"Error al almacenar documentos en MongoDB: {e}")

def main():
    """Función principal para ejecutar el proceso de ingesta."""
    logging.info("--- Iniciando el proceso de poblado de la Base de Conocimiento ---")
    
    collection = get_mongodb_collection()
    if collection is None:
        return

    # 1. Obtener contenido
    html_content = fetch_documentation_content()
    if not html_content:
        return

    # 2. Dividir en chunks
    text_chunks = chunk_content(html_content)
    if not text_chunks:
        return

    # 3. Generar embeddings
    embedded_chunks = generate_embeddings(text_chunks)
    if not embedded_chunks:
        return

    # 4. Almacenar en MongoDB
    store_in_mongodb(collection, embedded_chunks)

    logging.info("--- Proceso de poblado de la KB finalizado con éxito ---")

if __name__ == "__main__":
    main()