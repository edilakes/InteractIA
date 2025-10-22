
import os
import abc
import google.generativeai as genai
import json
import re
from PIL import Image

class ModelProvider(abc.ABC):
    """Clase base abstracta para cualquier proveedor de modelos de IA."""

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

class GeminiProvider(ModelProvider):
    """Proveedor para los modelos de Google Gemini."""
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.modelo = None # El modelo se establecerá después con set_model

    def set_model(self, model_name: str):
        self.modelo = genai.GenerativeModel(model_name)

    def list_models(self) -> list[str]:
        """Obtiene los modelos de Gemini que soportan generación de contenido."""
        try:
            return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            print(f"ERROR al listar modelos de Gemini: {e}")
            return []

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

# --- Factory y Loader ---

_PROVIDER_MAP = {
    "gemini": GeminiProvider
}

def get_model_provider(provider_config: dict) -> ModelProvider:
    """Factory que devuelve una instancia del proveedor según la configuración."""
    provider_type = provider_config.get("provider_type")
    if provider_type not in _PROVIDER_MAP:
        raise ValueError(f"Tipo de proveedor '{provider_type}' no soportado.")

    config = provider_config.get("config", {})
    api_key_env_var = config.get("api_key_env")
    api_key = os.getenv(api_key_env_var)

    if not api_key:
        raise ValueError(f"La variable de entorno '{api_key_env_var}' no está configurada.")

    ProviderClass = _PROVIDER_MAP[provider_type]
    return ProviderClass(api_key=api_key)

def load_providers_from_file(file_path: str = 'providers.json') -> list:
    """Carga la lista de configuraciones de proveedores desde un archivo JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ADVERTENCIA: El archivo '{file_path}' no fue encontrado.")
        return []
    except json.JSONDecodeError:
        print(f"ERROR: El archivo '{file_path}' tiene un formato JSON inválido.")
        return []
