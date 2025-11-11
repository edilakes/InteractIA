import os
import re
import pymongo
import datetime
from dotenv import load_dotenv
from model_manager import get_default_provider_config, get_model_provider
from config import MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_KB_COLLECTION

# --- Configuración ---
MANUAL_PATH = "docs/docs.md"
SOURCE_NAME = "docs/docs.md"
KNOWLEDGE_BASE_COLLECTION = MONGODB_KB_COLLECTION
DATABASE_NAME = MONGODB_DATABASE_NAME
VECTOR_INDEX_NAME = "vector_index"

def split_markdown_by_headers(content: str) -> list[dict[str, str]]:
    """
    Divide el contenido de un Markdown en trozos basados en los encabezados (## y ###).
    Cada trozo incluye el encabezado y el texto hasta el siguiente encabezado.
    """
    chunks = []
    # Divide por encabezados de nivel 2 (##)
    sections = re.split(r'(^## .*)', content, flags=re.MULTILINE)
    
    current_h2 = ""
    for i in range(1, len(sections), 2):
        header_h2 = sections[i].strip()
        text_h2 = sections[i+1]
        
        # Divide la sección por encabezados de nivel 3 (###)
        sub_sections = re.split(r'(^### .*)', text_h2, flags=re.MULTILINE)
        
        # El primer trozo es el texto bajo el H2 antes del primer H3
        if sub_sections[0].strip():
            chunks.append({
                "header": header_h2,
                "content": header_h2 + "\n" + sub_sections[0].strip()
            })

        # Procesa los trozos de los H3
        for j in range(1, len(sub_sections), 2):
            header_h3 = sub_sections[j].strip()
            text_h3 = sub_sections[j+1].strip()
            chunks.append({
                "header": f"{header_h2} > {header_h3}",
                "content": header_h3 + "\n" + text_h3
            })
            
    # Si no se encontraron encabezados H2, trata el documento como un solo trozo.
    if not chunks and content.strip():
        # Intenta dividir por H1
        sections_h1 = re.split(r'(^# .*)', content, flags=re.MULTILINE)
        if len(sections_h1) > 1:
             for i in range(1, len(sections_h1), 2):
                header_h1 = sections_h1[i].strip()
                text_h1 = sections_h1[i+1].strip()
                chunks.append({
                    "header": header_h1,
                    "content": header_h1 + "\n" + text_h1
                })
        else:
            chunks.append({
                "header": "General",
                "content": content.strip()
            })

    return chunks

def main():
    """
    Script principal para leer el manual, generar embeddings y guardarlos en MongoDB.
    """
    print("Iniciando el proceso de seeding de la Knowledge Base desde el manual.")

    # 1. Cargar configuración y conectar a la BD
    load_dotenv()
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        kb_collection = db[KNOWLEDGE_BASE_COLLECTION]
        print("Conexión a MongoDB establecida.")
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        return

    # 2. Asegurar que el índice vectorial exista
    try:
        index_info = kb_collection.list_search_indexes(name=VECTOR_INDEX_NAME)
        if not list(index_info):
            print(f"El índice vectorial '{VECTOR_INDEX_NAME}' no existe. Creándolo ahora...")
            kb_collection.create_search_index(
                name=VECTOR_INDEX_NAME,
                definition={
                    "mappings": {
                        "dynamic": True,
                        "fields": {
                            "embedding": {
                                "type": "vector",
                                "dimensions": 768, # Ajusta esto a la dimensión de tu modelo
                                "similarity": "cosine"
                            }
                        }
                    }
                }
            )
            print("Índice vectorial creado exitosamente.")
        else:
            print(f"El índice vectorial '{VECTOR_INDEX_NAME}' ya existe.")
    except Exception as e:
        print(f"Error al verificar o crear el índice vectorial: {e}")
        # Continuamos de todas formas, puede que la base de datos no soporte esta operación pero funcione.

    # 3. Cargar el proveedor de modelo por defecto
    try:
        provider_type, key_config, model_name = get_default_provider_config()
        model_provider = get_model_provider(provider_type, key_config)
        print(f"Proveedor de modelo '{provider_type}' cargado con el modelo '{model_name}'.")
    except Exception as e:
        print(f"Error al cargar el proveedor de modelo: {e}")
        return

    # 4. Leer y procesar el manual
    try:
        with open(MANUAL_PATH, 'r', encoding='utf-8') as f:
            manual_content = f.read()
        print(f"Manual '{MANUAL_PATH}' leído exitosamente.")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo del manual en '{MANUAL_PATH}'.")
        return

    chunks = split_markdown_by_headers(manual_content)
    if not chunks:
        print("No se pudieron extraer trozos del manual. Verifique el formato del archivo.")
        return
    
    print(f"Manual dividido en {len(chunks)} trozos.")

    # 5. Generar embeddings y guardar en la BD
    print("Generando embeddings y guardando en la base de datos... (esto puede tardar)")
    count_new = 0
    count_skipped = 0
    for chunk in chunks:
        content = chunk['content']
        
        # Verificar si el contenido ya existe para evitar duplicados
        if kb_collection.find_one({"text": content, "source": SOURCE_NAME}):
            print(f"Saltando trozo '{chunk['header']}' (ya existe en la BD).")
            count_skipped += 1
            continue

        try:
            # Generar embedding
            embedding = model_provider.embed_content(content)
            if not embedding:
                print(f"Error: No se pudo generar el embedding para el trozo: '{chunk['header']}'.")
                continue

            # Crear y guardar documento
            document = {
                "text": content,
                "embedding": embedding,
                "source": SOURCE_NAME,
                "timestamp": datetime.datetime.now(datetime.timezone.utc)
            }
            kb_collection.insert_one(document)
            count_new += 1
            print(f"Trozado '{chunk['header']}' guardado exitosamente.")

        except Exception as e:
            print(f"Error procesando el trozo '{chunk['header']}': {e}")

    print("\n--- Proceso de Seeding Finalizado ---")
    print(f"Trozos nuevos añadidos: {count_new}")
    print(f"Trozos omitidos (duplicados): {count_skipped}")
    print("La base de conocimiento ha sido actualizada con el contenido del manual.")

    client.close()

if __name__ == "__main__":
    main()