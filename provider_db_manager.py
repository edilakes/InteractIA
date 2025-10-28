from pymongo import MongoClient
from config import MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_PROVIDERS_COLLECTION

class ProviderDBManager:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGODB_DATABASE_NAME]
        self.collection = self.db[MONGODB_PROVIDERS_COLLECTION]

    def get_all_providers(self) -> list:
        """Recupera todos los documentos de proveedores."""
        return list(self.collection.find())

    def get_provider(self, provider_type: str) -> dict | None:
        """Recupera un proveedor por su tipo."""
        return self.collection.find_one({"provider_type": provider_type})

    def add_api_key_config(self, provider_type: str, api_key_config: dict):
        """Añade una nueva configuración de API key a un proveedor."""
        return self.collection.update_one(
            {"provider_type": provider_type},
            {"$push": {"api_key_configs": api_key_config}},
            upsert=True
        )

    def update_api_key_config(self, provider_type: str, key_name: str, new_config: dict):
        """Actualiza una configuración de API key existente."""
        return self.collection.update_one(
            {"provider_type": provider_type, "api_key_configs.name": key_name},
            {"$set": {"api_key_configs.$": new_config}}
        )

    def delete_api_key_config(self, provider_type: str, key_name: str):
        """Elimina una configuración de API key."""
        return self.collection.update_one(
            {"provider_type": provider_type},
            {"$pull": {"api_key_configs": {"name": key_name}}}
        )

    def update_models_for_api_key(self, provider_type: str, key_name: str, models: list):
        """Actualiza la lista de modelos para una API key específica."""
        return self.collection.update_one(
            {"provider_type": provider_type, "api_key_configs.name": key_name},
            {"$set": {"api_key_configs.$.available_models": models}}
        )

    def set_last_used_model(self, provider_type: str, key_name: str, model_name: str):
        """Marca un modelo como el último usado, y desmarca todos los demás."""
        # Desmarcar cualquier otro modelo que estuviera como último usado
        self.collection.update_many(
            {"api_key_configs.available_models.is_last_used": True},
            {"$set": {"api_key_configs.$[].available_models.$[].is_last_used": False}}
        )
        # Marcar el nuevo modelo como último usado
        return self.collection.update_one(
            {
                "provider_type": provider_type,
                "api_key_configs.name": key_name,
                "api_key_configs.available_models.name": model_name
            },
            {"$set": {"api_key_configs.$[key].available_models.$[model].is_last_used": True}},
            array_filters=[
                {"key.name": key_name},
                {"model.name": model_name}
            ]
        )

    def close_connection(self):
        """Cierra la conexión a la base de datos."""
        self.client.close()

# Global instance for easy access
provider_db_manager = ProviderDBManager()
