import pymongo
from config import MONGO_URI
import datetime
from datetime import timezone

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

    def guardar_habilidad(self, nombre_recurso, tipo_recurso, datos_habilidad):
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

    def consultar_habilidad(self, nombre_recurso):
        """
        Busca y devuelve una habilidad por su nombre.

        Args:
            nombre_recurso (str): El nombre del recurso a buscar.

        Returns:
            dict: El documento de la habilidad si se encuentra, de lo contrario None.
        """
        if not self.client:
            print("(-) No se puede consultar la habilidad, no hay conexión con la base de datos.")
            return None
            
        return self.collection.find_one({"nombre_recurso": nombre_recurso})

    def get_all_skills(self):
        """
        Devuelve todas las habilidades de la base de datos.

        Returns:
            list: Una lista de todas las habilidades.
        """
        if not self.client:
            print("(-) No se puede consultar las habilidades, no hay conexión con la base de datos.")
            return []
            
        return list(self.collection.find({}, {'_id': 0}))

if __name__ == '__main__':
    print("--- Probando el módulo KnowledgeBase ---")
    kb = KnowledgeBase()

    if kb.client: # Solo ejecutar si la conexión fue exitosa
        # Datos de prueba
        nombre_test = "api_prueba.com"
        datos_test = {
            "endpoint": "https://api_prueba.com/v1",
            "metodos": ["GET", "POST"],
            "ejemplo": "GET /v1/items"
        }

        # 1. Guardar la habilidad
        kb.guardar_habilidad(nombre_test, "API", datos_test)

        # 2. Consultar la habilidad
        habilidad_guardada = kb.consultar_habilidad(nombre_test)
        
        if habilidad_guardada:
            print("\n(+) Habilidad consultada:")
            print(habilidad_guardada)
            assert habilidad_guardada["datos"]["endpoint"] == "https://api_prueba.com/v1"
            print("\n(+) La aserción de datos fue exitosa.")
        else:
            print("(-) ERROR: No se pudo consultar la habilidad guardada.")

        # 3. Limpiar la base de datos
        kb.eliminar_habilidad(nombre_test)
        print("\n--- Prueba completada ---")
    else:
        print("\n--- Prueba abortada por fallo de conexión ---")
