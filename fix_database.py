
# Este script soluciona el problema de inicialización de la base de datos.
# Contiene el código necesario para insertar las habilidades fundamentales en la base de datos.

# Instrucciones:
# 1. Asegúrate de tener las dependencias de python instaladas (pymongo, python-dotenv).
# 2. Asegúrate de que tu archivo .env tiene la variable MONGO_URI configurada correctamente.
# 3. Ejecuta este script desde tu terminal: python fix_database.py

import os
import pymongo
from dotenv import load_dotenv
import datetime
from datetime import timezone

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")

class KnowledgeBase:
    """
    Gestiona la interacción con la base de datos de conocimiento en MongoDB.
    """
    def __init__(self, db_name="interactia_db", collection_name="habilidades"):
        """
        Inicializa la conexión a la base de datos y la colección.
        """
        self.client = None
        self.db = None
        self.collection = None
        try:
            if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
                raise ValueError("La URI de MongoDB no está configurada correctamente en el archivo .env")
            
            self.client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Forzar la conexión para verificar que es válida
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            print(f"(+) Conectado a MongoDB. Base de datos: '{db_name}', Colección: '{collection_name}'.")

        except (pymongo.errors.ConnectionFailure, pymongo.errors.ConfigurationError, ValueError) as e:
            print(f"(-) ERROR al inicializar KnowledgeBase: {e}")
            self.client = None # Asegurarse de que no se use un cliente inválido

    def aprender_habilidad(self, nombre_recurso, tipo_recurso, datos_habilidad):
        """
        Guarda o actualiza una habilidad en la base de datos.

        Args:
            nombre_recurso (str): El nombre único del recurso (ej. 'api.escriva.org').
            tipo_recurso (str): El tipo de recurso (ej. 'API', 'Sitio Web').
            datos_habilidad (dict): El diccionario con los datos estructurados de la habilidad.
        """
        if not self.client:
            print("(-) No se puede guardar la habilidad, no hay conexión con la base de datos.")
            return None

        documento = {
            "nombre_recurso": nombre_recurso,
            "tipo_recurso": tipo_recurso,
            "datos": datos_habilidad,
            "fecha_actualizacion": datetime.datetime.now(timezone.utc)
        }
        
        # Actualiza si existe, inserta si es nuevo (upsert)
        resultado = self.collection.update_one(
            {"nombre_recurso": nombre_recurso},
            {"$set": documento},
            upsert=True
        )
        
        if resultado.upserted_id:
            print(f"(+) Habilidad '{nombre_recurso}' guardada exitosamente (nuevo documento).")
            return resultado.upserted_id
        elif resultado.modified_count > 0:
            print(f"(+) Habilidad '{nombre_recurso}' actualizada exitosamente.")
            return self.collection.find_one({"nombre_recurso": nombre_recurso})["_id"]
        else:
            print(f"(+) La habilidad '{nombre_recurso}' ya estaba actualizada.")
            return self.collection.find_one({"nombre_recurso": nombre_recurso})["_id"]

habilidades_fundamentales = {
    "nombre_recurso": "habilidades_fundamentales_agente",
    "tipo_recurso": "Interno",
    "datos": {
        "descripcion": "Acciones primitivas que el agente puede ejecutar directamente sobre el sistema operativo. Son la base de todas las demás habilidades.",
        "contexto_aplicacion": ["General"],
        "acciones": [
            {
                "nombre": "clic",
                "descripcion": "Hace clic en un punto específico de la pantalla.",
                "parametros": [
                    {"nombre": "x_rel", "tipo": "float", "descripcion": "Coordenada X relativa (0.0 a 1.0)."},
                    {"nombre": "y_rel", "tipo": "float", "descripcion": "Coordenada Y relativa (0.0 a 1.0)."}
                ]
            },
            {
                "nombre": "escribir",
                "descripcion": "Escribe un texto en el campo de entrada activo.",
                "parametros": [
                    {"nombre": "texto", "tipo": "str", "descripcion": "El texto a escribir."}
                ]
            },
            {
                "nombre": "presionar_tecla",
                "descripcion": "Presiona una tecla o una combinación de teclas (ej. 'enter', 'ctrl+c').",
                "parametros": [
                    {"nombre": "tecla", "tipo": "str", "descripcion": "La tecla o combinación a presionar."}
                ]
            },
            {
                "nombre": "scroll",
                "descripcion": "Desplaza la rueda del ratón hacia arriba o hacia abajo.",
                "parametros": [
                    {"nombre": "direccion", "tipo": "str", "descripcion": "'arriba' o 'abajo'."},
                    {"nombre": "clics", "tipo": "int", "descripcion": "Número de 'clics' de la rueda."}
                ]
            },
            {
                "nombre": "arrastrar_barra",
                "descripcion": "Arrastra una barra de desplazamiento vertical.",
                "parametros": [
                    {"nombre": "direccion", "tipo": "str", "descripcion": "'arriba' o 'abajo'."},
                    {"nombre": "porcentaje", "tipo": "int", "descripcion": "Qué tanto arrastrar (0-100)."}
                ]
            },
            {
                "nombre": "cambiar_ventana",
                "descripcion": "Ejecuta Alt+Tab para cambiar de ventana.",
                "parametros": [
                    {"nombre": "tabs", "tipo": "int", "descripcion": "Número de veces que presionar Tab."}
                ]
            },
            {
                "nombre": "esperar",
                "descripcion": "Pausa la ejecución durante un número de segundos.",
                "parametros": [
                    {"nombre": "segundos", "tipo": "float", "descripcion": "Tiempo a esperar."}
                ]
            },
            {
                "nombre": "hablar",
                "descripcion": "Comunica un mensaje verbal al usuario a través de la interfaz.",
                "parametros": [
                    {"nombre": "mensaje", "tipo": "str", "descripcion": "El mensaje a mostrar al usuario."}
                ]
            },
            {
                "nombre": "pedir_aclaracion",
                "descripcion": "Hace una pregunta al usuario para obtener más información.",
                "parametros": [
                    {"nombre": "pregunta", "tipo": "str", "descripcion": "La pregunta para el usuario."}
                ]
            },
            {
                "nombre": "finalizar",
                "descripcion": "Finaliza la tarea actual y reporta el resultado.",
                "parametros": [
                    {"nombre": "razon", "tipo": "str", "descripcion": "La razón por la que la tarea ha finalizado."}
                ]
            },
            {
                "nombre": "proponer_aprendizaje",
                "descripcion": "Propone al usuario guardar una nueva habilidad aprendida.",
                "parametros": [
                    {"nombre": "nombre_habilidad", "tipo": "str", "descripcion": "Nombre propuesto para la habilidad."},
                    {"nombre": "descripcion", "tipo": "str", "descripcion": "Descripción de lo que hace la habilidad."}
                ]
            }
        ]
    }
}

if __name__ == "__main__":
    kb = KnowledgeBase()
    if kb.client:
        kb.aprender_habilidad(
            habilidades_fundamentales["nombre_recurso"],
            habilidades_fundamentales["tipo_recurso"],
            habilidades_fundamentales["datos"]
        )
        print("Habilidades fundamentales insertadas correctamente.")
    else:
        print("No se pudo conectar a la base de datos.")
