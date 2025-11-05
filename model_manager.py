import os
import abc
import google.generativeai as genai
import json
import re
from PIL import Image
from provider_db_manager import provider_db_manager

class ModelProvider(abc.ABC):
    """Clase base abstracta para un proveedor de modelos."""
    def __init__(self, api_key_config: dict):
        self.api_key_config = api_key_config
        self.provider_type = None # Se debe establecer en la subclase

    @abc.abstractmethod
    def set_model(self, model_name: str):
        pass

    @abc.abstractmethod
    def list_models(self) -> list[str]:
        pass

    @abc.abstractmethod
    def generate_content(self, prompt: str, image: Image.Image = None) -> dict:
        pass

    @abc.abstractmethod
    def embed_content(self, text: str) -> list[float]:
        """Genera un vector de embedding para un texto dado."""
        pass

    @abc.abstractmethod
    def refresh_available_models(self):
        pass

class GeminiProvider(ModelProvider):
    """Proveedor para los modelos de Google Gemini."""
    def __init__(self, api_key_config: dict):
        super().__init__(api_key_config)
        self.provider_type = "gemini"
        
        api_key_env_var = self.api_key_config.get("api_key_env_name")
        if not api_key_env_var:
            raise ValueError("La configuración de API key no especifica 'api_key_env_name'.")

        api_key = os.getenv(api_key_env_var)
        if not api_key:
            raise ValueError(f"La variable de entorno '{api_key_env_var}' no está configurada o está vacía.")
        
        genai.configure(api_key=api_key)
        self.modelo = None
        # TODO: Hacer que el modelo de embedding sea configurable
        self.embedding_model = "models/embedding-001"

    def set_model(self, model_name: str):
        self.modelo = genai.GenerativeModel(model_name)
        update_last_used_model(self.provider_type, self.api_key_config['name'], model_name)

    def list_models(self) -> list[str]:
        return [model["name"] for model in self.api_key_config.get("models", [])]

    def _check_model_is_set(self):
        if not self.modelo:
            raise RuntimeError("El modelo no ha sido establecido. Llama a set_model() antes.")

    def generate_content(self, prompt: str, image: Image.Image = None) -> dict:
        self._check_model_is_set()
        try:
            args = [prompt]
            if image:
                args.append(image)
            
            response = self.modelo.generate_content(args)
            
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return {"text": response.text}
            
            return {"text": response.text}

        except Exception as e:
            print(f"ERROR en GeminiProvider (generate_content): {e}")
            return {"error": str(e)}

    def embed_content(self, text: str) -> list[float]:
        """Genera un embedding para el texto usando el modelo de embedding de Gemini."""
        try:
            result = genai.embed_content(model=self.embedding_model, content=text)
            return result['embedding']
        except Exception as e:
            print(f"ERROR en GeminiProvider (embed_content): {e}")
            return None

    def refresh_available_models(self):
        print(f"Refrescando modelos para {self.api_key_config.get('name')}...")
        try:
            # Actualizado para incluir modelos de embedding
            current_model_names = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods or 'embedContent' in m.supported_generation_methods]
            
            old_models = self.api_key_config.get("models", [])
            last_used_model = next((m["name"] for m in old_models if m.get("is_last_used")), None)

            new_models = [{"name": name, "is_last_used": name == last_used_model} for name in current_model_names]
            
            if not any(m["is_last_used"] for m in new_models) and new_models:
                new_models[0]["is_last_used"] = True

            provider_db_manager.update_models_for_api_key(self.provider_type, self.api_key_config['name'], new_models)
            print(f"Modelos para {self.api_key_config.get('name')} actualizados.")
        except Exception as e:
            print(f"ERROR al refrescar modelos: {e}")

PROVIDER_MAP = {"gemini": GeminiProvider}

def update_last_used_model(provider_type: str, key_name: str, model_name: str):
    """Actualiza el flag is_last_used para el modelo especificado."""
    try:
        provider_db_manager.set_last_used_model(provider_type, key_name, model_name)
    except Exception as e:
        print(f"ERROR al actualizar el último modelo usado: {e}")

def load_providers_from_db() -> list:
    """Carga todas las configuraciones de proveedores desde la base de datos."""
    return provider_db_manager.get_all_providers()

def get_default_provider_config() -> tuple[str, dict, str]:
    """Obtiene el tipo de proveedor, la config de API key y el nombre del modelo por defecto."""
    providers = load_providers_from_db()
    if not providers:
        raise RuntimeError("No se encontraron proveedores en la base de datos.")

    # Prioritize the last used model
    for provider in providers:
        for key_config in provider.get("api_keys", []):
            for model in key_config.get("models", []):
                if model.get("is_last_used"):
                    return provider["provider_type"], key_config, model["name"]

    # If no last used model, find the first valid key
    for provider in providers:
        for key_config in provider.get("api_keys", []):
            api_key_env_name = key_config.get("api_key_env_name")
            if api_key_env_name and os.getenv(api_key_env_name):
                if key_config.get("models"):
                    model = key_config["models"][0]
                    return provider["provider_type"], key_config, model["name"]

    raise RuntimeError("No se pudo determinar una configuración de proveedor y modelo por defecto.")

def get_model_provider(provider_type: str = None, api_key_config: dict = None) -> ModelProvider:
    """Factory que devuelve una instancia del proveedor."""
    selected_provider_type = provider_type
    selected_api_key_config = api_key_config
    selected_model_name = None

    if not selected_provider_type or not selected_api_key_config:
        selected_provider_type, selected_api_key_config, selected_model_name = get_default_provider_config()

    ProviderClass = PROVIDER_MAP.get(selected_provider_type)
    if not ProviderClass:
        raise ValueError(f"Tipo de proveedor '{selected_provider_type}' no soportado.")

    instance = ProviderClass(api_key_config=selected_api_key_config)
    
    model_to_set = selected_model_name
    if not model_to_set and selected_api_key_config.get("models"):
        # Prioritize non-embedding models for general use
        generative_models = [m["name"] for m in selected_api_key_config["models"] if 'embed' not in m["name"]]
        if generative_models:
            model_to_set = generative_models[0]
    
    if model_to_set:
        instance.set_model(model_to_set)

    return instance

def refresh_provider_models(provider_type: str, key_name: str):
    """Refresca los modelos para una configuración de API key específica."""
    provider = provider_db_manager.get_provider(provider_type)
    if not provider:
        print(f"ADVERTENCIA: No se encontró el proveedor '{provider_type}'.")
        return

    key_config = next((k for k in provider.get("api_keys", []) if k['name'] == key_name), None)
    if not key_config:
        print(f"ADVERTENCIA: No se encontró la config de API key '{key_name}'.")
        return

    try:
        provider_instance = get_model_provider(provider_type, key_config)
        provider_instance.refresh_available_models()
    except Exception as e:
        print(f"ERROR al refrescar modelos para {key_name}: {e}")
