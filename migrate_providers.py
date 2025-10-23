import json
from provider_db_manager import provider_db_manager

def migrate_providers_to_mongodb():
    try:
        with open("providers.json", "r", encoding="utf-8") as f:
            providers_data = json.load(f)
        
        for provider in providers_data:
            # Ensure 'id' field is a string, not ObjectId, for consistency with how we retrieve
            # and to avoid issues if it's already an ObjectId string from a previous run
            if '_id' in provider:
                provider['id'] = str(provider['_id'])
                del provider['_id']
            
            # Check if a provider with this 'id' already exists in DB
            # If 'id' is not a valid ObjectId, find_one will return None for _id search
            existing_provider = provider_db_manager.get_provider_by_id(provider.get("id"))
            if not existing_provider:
                provider_db_manager.insert_provider(provider)
                print(f"Inserted provider: {provider.get("name")}")
            else:
                print(f"Provider already exists, skipping: {provider.get("name")}")

        print("Migration complete.")
    except FileNotFoundError:
        print("providers.json not found. Skipping migration.")
    except Exception as e:
        print(f"An error occurred during migration: {e}")

if __name__ == "__main__":
    migrate_providers_to_mongodb()
    provider_db_manager.close_connection()
