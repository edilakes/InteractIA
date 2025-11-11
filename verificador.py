import logging
from vision import find_text_on_screen
from PIL import Image
import cv2
import numpy as np

class Verificador:
    def __init__(self, model_provider):
        self.logger = logging.getLogger("InteractIA")
        self.model_provider = model_provider

    def verificar_accion(self, accion: str, argumentos: dict, pre_screenshot_path: str, post_screenshot_path: str) -> dict:
        self.logger.info(f"Verificando la acción '{accion}'...")

        if accion == "escribir":
            return self._verificar_escribir(argumentos, post_screenshot_path)
        elif accion == "clic":
            return self._verificar_clic(argumentos, pre_screenshot_path, post_screenshot_path)
        else:
            return self._verificar_generico(accion, pre_screenshot_path, post_screenshot_path)

    def _verificar_escribir(self, argumentos: dict, post_screenshot_path: str) -> dict:
        texto_esperado = argumentos.get("texto")
        if not texto_esperado:
            return {"verificado": False, "confianza": 1.0, "razon": "No se proporcionó texto para verificar."}

        mouse_pos = argumentos.get("mouse_pos")
        if not mouse_pos:
            # Fallback to searching the whole screen if mouse position is not available
            analisis_post = find_text_on_screen(texto_esperado)
            if analisis_post:
                return {"verificado": True, "confianza": 0.8, "razon": f"El texto '{texto_esperado}' fue encontrado en la pantalla (sin posición específica)."}
            else:
                return {"verificado": False, "confianza": 0.7, "razon": f"El texto '{texto_esperado}' no fue encontrado en la pantalla."}

        # Search for the text in a region around the mouse cursor
        try:
            img = cv2.imread(post_screenshot_path)
            h, w, _ = img.shape
            
            # Define a search area around the cursor
            roi_size_x = 200  # Wider search area for text
            roi_size_y = 40
            x_start = max(0, mouse_pos[0] - roi_size_x // 2)
            y_start = max(0, mouse_pos[1] - roi_size_y // 2)
            x_end = min(w, mouse_pos[0] + roi_size_x // 2)
            y_end = min(h, mouse_pos[1] + roi_size_y // 2)

            roi = img[y_start:y_end, x_start:x_end]
            
            # Use pytesseract to find text in the ROI
            import pytesseract
            text_in_roi = pytesseract.image_to_string(roi)

            if texto_esperado in text_in_roi:
                return {"verificado": True, "confianza": 0.95, "razon": f"El texto '{texto_esperado}' fue encontrado cerca de la posición del cursor."}
            else:
                return {"verificado": False, "confianza": 0.85, "razon": f"El texto '{texto_esperado}' no fue encontrado cerca de la posición del cursor. Texto encontrado: '{text_in_roi[:100]}...'"}

        except Exception as e:
            self.logger.error(f"Error durante la verificación de escritura: {e}", exc_info=True)
            return {"verificado": False, "confianza": 0.3, "razon": f"Error técnico durante la verificación de escritura: {e}"}


    def _verificar_clic(self, argumentos: dict, pre_screenshot_path: str, post_screenshot_path: str) -> dict:
        x = argumentos.get("x")
        y = argumentos.get("y")

        if x is None or y is None:
            return self._verificar_generico("clic", pre_screenshot_path, post_screenshot_path)

        try:
            pre_img = cv2.imread(pre_screenshot_path)
            post_img = cv2.imread(post_screenshot_path)

            roi_size = 30
            half_size = roi_size // 2
            
            h, w, _ = pre_img.shape
            x_start = max(0, x - half_size)
            y_start = max(0, y - half_size)
            x_end = min(w, x + half_size)
            y_end = min(h, y + half_size)

            pre_roi = pre_img[y_start:y_end, x_start:x_end]
            post_roi = post_img[y_start:y_end, x_start:x_end]

            if pre_roi.shape != post_roi.shape:
                return {"verificado": True, "confianza": 0.7, "razon": "Las dimensiones del ROI cambiaron, lo que indica un cambio significativo."}

            from skimage.metrics import structural_similarity as ssim
            
            pre_roi_gray = cv2.cvtColor(pre_roi, cv2.COLOR_BGR2GRAY)
            post_roi_gray = cv2.cvtColor(post_roi, cv2.COLOR_BGR2GRAY)
            
            similarity_index, _ = ssim(pre_roi_gray, post_roi_gray, full=True)

            self.logger.info(f"Índice de similitud estructural (SSI) para el clic: {similarity_index:.4f}")

            if similarity_index > 0.9:
                return {"verificado": False, "confianza": 0.8, "razon": f"El área alrededor del clic ({x},{y}) no cambió significativamente (similitud: {similarity_index:.2f})."}
            else:
                return {"verificado": True, "confianza": 0.9, "razon": f"El área alrededor del clic ({x},{y}) cambió (similitud: {similarity_index:.2f}), lo que sugiere que el clic tuvo un efecto."}

        except Exception as e:
            self.logger.error(f"Error durante la verificación del clic: {e}", exc_info=True)
            return {"verificado": False, "confianza": 0.3, "razon": f"Error técnico durante la verificación: {e}"}


    def _verificar_generico(self, accion: str, pre_screenshot_path: str, post_screenshot_path: str) -> dict:
        try:
            pre_img = cv2.imread(pre_screenshot_path)
            post_img = cv2.imread(post_screenshot_path)

            if pre_img.shape != post_img.shape:
                return {"verificado": True, "confianza": 0.6, "razon": "Las dimensiones de la pantalla cambiaron."}

            from skimage.metrics import structural_similarity as ssim
            pre_gray = cv2.cvtColor(pre_img, cv2.COLOR_BGR2GRAY)
            post_gray = cv2.cvtColor(post_img, cv2.COLOR_BGR2GRAY)
            
            similarity_index, _ = ssim(pre_gray, post_gray, full=True)

            if similarity_index > 0.98:
                return {"verificado": False, "confianza": 0.7, "razon": f"La pantalla no cambió significativamente después de la acción '{accion}' (similitud: {similarity_index:.2f})."}
            else:
                return {"verificado": True, "confianza": 0.5, "razon": f"La pantalla cambió después de la acción '{accion}' (similitud: {similarity_index:.2f})."}
        except Exception as e:
            self.logger.error(f"Error durante la verificación genérica: {e}", exc_info=True)
            return {"verificado": False, "confianza": 0.3, "razon": f"Error técnico durante la verificación genérica: {e}"}

if __name__ == '__main__':
    class MockModelProvider:
        def generate_content(self, prompt):
            return {"text": "Mocked response"}

    verificador = Verificador(MockModelProvider())
    
    print("Verificador module loaded.")
