import os
import pymongo
from dotenv import load_dotenv
from datetime import datetime
from bson.objectid import ObjectId

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
CONSIDERATIONS_COLLECTION = "consideraciones"

class ConsiderationsDBManager:
    def __init__(self):
        if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
            raise ValueError("La variable de entorno MONGO_URI no está configurada o es inválida.")
        self.client = pymongo.MongoClient(MONGO_URI)
        self.db = self.client[MONGODB_DATABASE_NAME]
        self.collection = self.db[CONSIDERATIONS_COLLECTION]

    def get_all_considerations(self):
        return list(self.collection.find({}).sort("nombre", pymongo.ASCENDING))

    def add_consideration(self, nombre: str, contenido: str):
        if not nombre or not contenido:
            raise ValueError("Nombre y contenido no pueden estar vacíos.")
        
        # Verificar si ya existe una consideración con el mismo nombre
        if self.collection.find_one({"nombre": nombre}):
            raise ValueError(f"Ya existe una consideración con el nombre '{nombre}'.")

        consideration = {
            "nombre": nombre,
            "contenido": contenido,
            "fecha_creacion": datetime.now(),
            "fecha_actualizacion": datetime.now()
        }
        result = self.collection.insert_one(consideration)
        return str(result.inserted_id)

    def update_consideration(self, id: str, nombre: str, contenido: str):
        if not id or not nombre or not contenido:
            raise ValueError("ID, nombre y contenido no pueden estar vacíos.")
        
        # Verificar si el nuevo nombre ya existe en otra consideración
        existing_consideration = self.collection.find_one({"nombre": nombre})
        if existing_consideration and str(existing_consideration["_id"]) != id:
            raise ValueError(f"Ya existe otra consideración con el nombre '{nombre}'.")

        result = self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "nombre": nombre,
                "contenido": contenido,
                "fecha_actualizacion": datetime.now()
            }}
        )
        return result.modified_count > 0

    def delete_consideration(self, id: str):
        if not id:
            raise ValueError("El ID no puede estar vacío.")
        result = self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    def get_consideration_by_name(self, nombre: str):
        return self.collection.find_one({"nombre": nombre})

    def close_connection(self):
        self.client.close()

considerations_db_manager = ConsiderationsDBManager()
