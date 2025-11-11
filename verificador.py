import logging
from vision import verify_image_with_description

class Verificador:
    def __init__(self, model_provider):
        self.logger = logging.getLogger("InteractIA")
        self.model_provider = model_provider

    def verificar_accion(self, accion: str, argumentos: dict, pre_screenshot_path: str, post_screenshot_path: str, expected_outcome: str, mouse_pos: dict) -> dict:
        self.logger.info(f"Verificando la acción '{accion}' con resultado esperado: '{expected_outcome}'")

        if not expected_outcome or expected_outcome == "No se proporcionó una descripción del resultado esperado.":
            self.logger.warning("No se proporcionó un resultado esperado. No se puede realizar la verificación.")
            return {"verificado": False, "confianza": 0.0, "razon": "No se proporcionó un resultado esperado."}

        return verify_image_with_description(post_screenshot_path, expected_outcome)

if __name__ == '__main__':
    class MockModelProvider:
        def generate_content(self, prompt):
            return {"text": "Mocked response"}

    verificador = Verificador(MockModelProvider())
    
    print("Verificador module loaded.")