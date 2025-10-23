from pymongo import MongoClient
from bson.objectid import ObjectId
from config import MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_PROVIDERS_COLLECTION

class ProviderDBManager:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGODB_DATABASE_NAME]
        self.collection = self.db[MONGODB_PROVIDERS_COLLECTION]

    def get_all_providers(self) -> list:
        """Recupera todas las configuraciones de proveedores de la base de datos."""
        providers = []
        for doc in self.collection.find():
            # Convert ObjectId to string for JSON serialization if needed later
            if '_id' in doc:
                doc['id'] = str(doc['_id'])
                del doc['_id']
            providers.append(doc)
        return providers

    def get_provider_by_id(self, provider_id: str) -> dict | None:
        """Recupera una configuración de proveedor por su ID."""
        # Assuming 'id' field in documents is the string representation of ObjectId
        # or a custom string ID. If it's ObjectId, we need to convert.
        try:
            doc = self.collection.find_one({'_id': ObjectId(provider_id)})
        except:
            doc = self.collection.find_one({'id': provider_id})

        if doc and '_id' in doc:
            doc['id'] = str(doc['_id'])
            del doc['_id']
        return doc

    def update_provider(self, provider_id: str, new_data: dict):
        """Actualiza una configuración de proveedor existente."""
        # Remove 'id' from new_data if it's present, as _id is immutable
        data_to_update = new_data.copy()
        if 'id' in data_to_update:
            del data_to_update['id']

        try:
            result = self.collection.update_one({'_id': ObjectId(provider_id)}, {'$set': data_to_update})
        except:
            result = self.collection.update_one({'id': provider_id}, {'$set': data_to_update})
        return result.modified_count > 0

    def insert_provider(self, provider_data: dict):
        """Inserta una nueva configuración de proveedor."""
        # If provider_data has an 'id' field, it might conflict with MongoDB's _id
        # It's better to let MongoDB generate _id and use 'id' as a custom field if needed.
        # For now, we'll remove 'id' if it's a string that looks like an ObjectId
        # and let MongoDB generate _id.
        data_to_insert = provider_data.copy()
        if 'id' in data_to_insert and ObjectId.is_valid(data_to_insert['id']):
            del data_to_insert['id'] # Let MongoDB generate _id
        
        result = self.collection.insert_one(data_to_insert)
        return str(result.inserted_id)

    def delete_provider(self, provider_id: str):
        """Elimina una configuración de proveedor por su ID."""
        try:
            result = self.collection.delete_one({'_id': ObjectId(provider_id)})
        except:
            result = self.collection.delete_one({'id': provider_id})
        return result.deleted_count > 0

    def close_connection(self):
        """Cierra la conexión a la base de datos."""
        self.client.close()

# Global instance for easy access
provider_db_manager = ProviderDBManager()
