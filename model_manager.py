import os
import abc
import google.generativeai as genai
import json
import re
from PIL import Image

# Helper function to write providers data to file
def _write_providers_to_file(providers_data: list, file_path: str = 'providers.json'):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_file_path = os.path.join(script_dir, file_path)
    try:
        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            json.dump(providers_data, f, indent=2)
    except IOError as e:
        print(f"ERROR al escribir en el archivo de proveedores '{absolute_file_path}': {e}")

class ModelProvider(abc.ABC):
    """Clase base abstracta para cualquier proveedor de modelos de IA."""

    def __init__(self, provider_config: dict):
        self.provider_config = provider_config
        self.provider_id = provider_config.get("id")

    @abc.abstractmethod
    def set_model(self, model_name: str):
        """Configura el modelo específico a utilizar para las generaciones."""
        pass

    @abc.abstractmethod
    def list_models(self) -> list[str]:
        """Devuelve una lista de los nombres de los modelos de chat disponibles."""
        pass

    @abc.abstractmethod
    def generate_content(self, prompt: str, image: Image.Image) -> dict:
        """Genera una decisión estructurada (JSON) a partir de un prompt y una imagen."""
        pass

    @abc.abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Genera una respuesta de texto simple a partir de un prompt."""
        pass

    @abc.abstractmethod
    def refresh_available_models(self):
        """Actualiza la lista de modelos disponibles para este proveedor."""
        pass

class GeminiProvider(ModelProvider):
    """Proveedor para los modelos de Google Gemini."""
    def __init__(self, provider_config: dict):
        super().__init__(provider_config)
        api_key_env_var = self.provider_config.get("config", {}).get("api_key_env")
        api_key = os.getenv(api_key_env_var)
        if not api_key:
            raise ValueError(f"La variable de entorno '{api_key_env_var}' no está configurada para el proveedor {self.provider_id}.")
        genai.configure(api_key=api_key)
        self.modelo = None # El modelo se establecerá después con set_model

    def set_model(self, model_name: str):
        self.modelo = genai.GenerativeModel(model_name)
        _update_last_used_model(self.provider_id, model_name)

    def list_models(self) -> list[str]:
        """Devuelve una lista de los nombres de los modelos de chat disponibles desde la configuración estática."""
        return [model["name"] for model in self.provider_config.get("available_models", [])]

    def _check_model_is_set(self):
        if not self.modelo:
            raise RuntimeError("El modelo no ha sido establecido. Llama a set_model() antes de generar contenido.")

    def generate_content(self, prompt: str, image: Image.Image) -> dict:
        self._check_model_is_set()
        contenido = [prompt]
        if image:
            contenido.append(image)
        try:
            respuesta = self.modelo.generate_content(contenido)
            match = re.search(r'\{.*\}', respuesta.text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                raise json.JSONDecodeError("No se encontró un objeto JSON en la respuesta.", respuesta.text, 0)
        except Exception as e:
            print(f"ERROR en GeminiProvider (generate_content): {e}")
            raise

    def generate_text(self, prompt: str) -> str:
        self._check_model_is_set()
        try:
            respuesta = self.modelo.generate_content(prompt)
            return respuesta.text.strip()
        except Exception as e:
            print(f"ERROR en GeminiProvider (generate_text): {e}")
            raise

    def refresh_available_models(self):
        """Actualiza la lista de modelos disponibles para este proveedor desde la API de Gemini."""
        print(f"Refrescando modelos para el proveedor {self.provider_id}...")
        try:
            current_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Cargar la configuración actual de providers.json
            script_dir = os.path.dirname(os.path.abspath(__file__))
            absolute_file_path = os.path.join(script_dir, 'providers.json')
            with open(absolute_file_path, 'r', encoding='utf-8') as f:
                providers_data = json.load(f)

            for provider_config in providers_data:
                if provider_config.get("id") == self.provider_id:
                    # Preservar el estado de is_last_used si el modelo sigue existiendo
                    old_available_models = provider_config.get("available_models", [])
                    new_available_models = []
                    last_used_model_name = None

                    for old_model in old_available_models:
                        if old_model.get("is_last_used"):
                            last_used_model_name = old_model.get("name")
                            break

                    for model_name in current_models:
                        is_last_used = (model_name == last_used_model_name)
                        new_available_models.append({"name": model_name, "is_last_used": is_last_used})
                    
                    # Si el last_used_model ya no existe, o no había uno, marcar el primero como last_used
                    if not any(model.get("is_last_used") for model in new_available_models) and new_available_models:
                        new_available_models[0]["is_last_used"] = True

                    provider_config["available_models"] = new_available_models
                    break
            
            _write_providers_to_file(providers_data)
            print(f"Modelos para {self.provider_id} actualizados correctamente.")

        except Exception as e:
            print(f"ERROR al refrescar modelos para {self.provider_id}: {e}")

# --- Factory y Loader ---

_PROVIDER_MAP = {
    "gemini": GeminiProvider
}

def _update_last_used_model(provider_id: str, model_name: str):
    """Actualiza el flag is_last_used para el modelo y proveedor especificados en providers.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_file_path = os.path.join(script_dir, 'providers.json')
    try:
        with open(absolute_file_path, 'r', encoding='utf-8') as f:
            providers_data = json.load(f)

        found = False
        for provider_config in providers_data:
            if provider_config.get("id") == provider_id:
                if "available_models" in provider_config:
                    for model in provider_config["available_models"]:
                        if model.get("name") == model_name:
                            model["is_last_used"] = True
                            found = True
                        else:
                            model["is_last_used"] = False
                break
        
        if found:
            _write_providers_to_file(providers_data)
        else:
            print(f"ADVERTENCIA: No se encontró el modelo '{model_name}' para el proveedor '{provider_id}' al intentar actualizar el estado de último usado.")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR al actualizar el estado de último modelo usado: {e}")

def load_providers_from_file(file_path: str = 'providers.json') -> list:
    """Carga la lista de configuraciones de proveedores desde un archivo JSON."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_file_path = os.path.join(script_dir, file_path)
    try:
        with open(absolute_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ADVERTENCIA: El archivo '{absolute_file_path}' no fue encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"ERROR: El archivo '{absolute_file_path}' tiene un formato JSON inválido.")
        return []

def get_default_provider_config() -> tuple[dict, str]:
    """Obtiene la configuración del proveedor y el nombre del modelo por defecto o el último usado."""
    providers = load_providers_from_file()
    if not providers:
        raise RuntimeError("No se encontraron configuraciones de proveedores.")

    default_provider_config = None
    default_model_name = None

    # Buscar el último modelo usado
    for provider_config in providers:
        if "available_models" in provider_config:
            for model in provider_config["available_models"]:
                if model.get("is_last_used"):
                    default_provider_config = provider_config
                    default_model_name = model["name"]
                    break
        if default_provider_config:
            break

    # Si no se encontró un último modelo usado, tomar el primero disponible
    if not default_provider_config:
        for provider_config in providers:
            if "available_models" in provider_config and provider_config["available_models"]:
                default_provider_config = provider_config
                default_model_name = provider_config["available_models"][0]["name"]
                break
    
    if not default_provider_config or not default_model_name:
        raise RuntimeError("No se pudo determinar una configuración de proveedor y modelo por defecto.")

    return default_provider_config, default_model_name

def get_model_provider(provider_config: dict = None) -> ModelProvider:
    """Factory que devuelve una instancia del proveedor según la configuración.
    Si no se proporciona provider_config, intenta cargar el último usado o el por defecto.
    """
    selected_provider_config = provider_config
    selected_model_name = None

    if selected_provider_config is None:
        selected_provider_config, selected_model_name = get_default_provider_config()

    provider_type = selected_provider_config.get("provider_type")
    if provider_type not in _PROVIDER_MAP:
        raise ValueError(f"Tipo de proveedor '{provider_type}' no soportado.")

    ProviderClass = _PROVIDER_MAP[provider_type]
    # Pasar la configuración completa del proveedor a la instancia del proveedor
    instance = ProviderClass(provider_config=selected_provider_config)
    
    # Si se obtuvo un selected_model_name del default, establecerlo
    if selected_model_name:
        instance.set_model(selected_model_name)

    return instance

def refresh_provider_models(provider_id: str):
    """Refresca la lista de modelos disponibles para un proveedor específico.
    Esta función puede ser llamada desde la GUI para actualizar los modelos.
    """
    providers_data = load_providers_from_file()
    target_provider_config = None
    for p_config in providers_data:
        if p_config.get("id") == provider_id:
            target_provider_config = p_config
            break

    if target_provider_config:
        try:
            # Crear una instancia temporal del proveedor para llamar a refresh_available_models
            provider_instance = get_model_provider(provider_config=target_provider_config)
            provider_instance.refresh_available_models()
        except Exception as e:
            print(f"ERROR al intentar refrescar modelos para el proveedor {provider_id}: {e}")
    else:
        print(f"ADVERTENCIA: No se encontró el proveedor con ID '{provider_id}' para refrescar modelos.")