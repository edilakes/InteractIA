from pymongo import MongoClient
from config import MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_PROVIDERS_COLLECTION

class ProviderDBManager:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGODB_DATABASE_NAME]
        self.collection = self.db[MONGODB_PROVIDERS_COLLECTION]

    def get_all_providers(self) -> list:
        """Recupera la lista de proveedores del documento único."""
        config_doc = self.collection.find_one()
        return config_doc.get("providers", []) if config_doc else []

    def get_provider(self, provider_type: str) -> dict | None:
        """Recupera un proveedor por su tipo desde el documento único."""
        providers = self.get_all_providers()
        return next((p for p in providers if p.get("provider_type") == provider_type), None)

    def add_api_key_config(self, provider_type: str, api_key_config: dict):
        """Añade una nueva configuración de API key a un proveedor."""
        return self.collection.update_one(
            {"providers.provider_type": provider_type},
            {"$push": {"providers.$.api_keys": api_key_config}}
        )

    def update_api_key_config(self, provider_type: str, key_name: str, new_config: dict):
        """Actualiza una configuración de API key existente."""
        return self.collection.update_one(
            {"providers.provider_type": provider_type, "providers.api_keys.name": key_name},
            {"$set": {"providers.$[provider].api_keys.$[key]": new_config}},
            array_filters=[
                {"provider.provider_type": provider_type},
                {"key.name": key_name}
            ]
        )

    def delete_api_key_config(self, provider_type: str, key_name: str):
        """Elimina una configuración de API key."""
        return self.collection.update_one(
            {"providers.provider_type": provider_type},
            {"$pull": {"providers.$.api_keys": {"name": key_name}}}
        )

    def update_models_for_api_key(self, provider_type: str, key_name: str, models: list):
        """Actualiza la lista de modelos para una API key específica."""
        return self.collection.update_one(
            {"providers.provider_type": provider_type, "providers.api_keys.name": key_name},
            {"$set": {"providers.$[provider].api_keys.$[key].models": models}},
            array_filters=[
                {"provider.provider_type": provider_type},
                {"key.name": key_name}
            ]
        )

    def set_last_used_model(self, provider_type: str, key_name: str, model_name: str):
        """Marca un modelo como el último usado, y desmarca todos los demás."""
        # Desmarcar todos los modelos en toda la colección
        self.collection.update_one(
            {},
            {"$set": {"providers.$[].api_keys.$[].models.$[].is_last_used": False}}
        )
        # Marcar el nuevo modelo como último usado
        return self.collection.update_one(
            {
                "providers.provider_type": provider_type,
                "providers.api_keys.name": key_name,
                "providers.api_keys.models.name": model_name
            },
            {"$set": {"providers.$[p].api_keys.$[k].models.$[m].is_last_used": True}},
            array_filters=[
                {"p.provider_type": provider_type},
                {"k.name": key_name},
                {"m.name": model_name}
            ]
        )

    def close_connection(self):
        """Cierra la conexión a la base de datos."""
        self.client.close()

# Global instance for easy access
provider_db_manager = ProviderDBManager()