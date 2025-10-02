import time
import json
import google.generativeai as genai
from PIL import Image
import pyautogui # Importar para obtener la ventana activa
import logging

# Módulos de la aplicación
import config
from controlador import Controlador
from vision import Vision
from knowledge_base import KnowledgeBase
from logger_config import setup_logging

class Agente:
    """
    El agente principal que orquesta los módulos de percepción, decisión y acción.
    """
    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger("InteractIA")
        self.logger.info("Inicializando el agente InteractIA...")
        # --- Cargar configuración y verificar ---
        if not config.verificar_configuracion():
            self.operativo = False
            self.logger.error("El agente no puede operar debido a una configuración faltante.")
            return
        
        # --- Inicializar módulos ---
        self.controlador = Controlador()
        self.vision = Vision()
        self.kb = KnowledgeBase()
        self.objetivo = None
        self.historial_acciones = []

        # --- Configurar el modelo de IA ---
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.modelo = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
            self.logger.info("Modelo de IA configurado exitosamente.")
            self.operativo = True
        except Exception as e:
            self.logger.error(f"ERROR al configurar el modelo de IA: {e}")
            self.operativo = False

    def establecer_objetivo(self, objetivo):
        self.objetivo = objetivo
        self.logger.info(f"Objetivo establecido: {self.objetivo}")

    def observar(self):
        self.logger.info("--- Fase: Observar ---")
        titulo_ventana = pyautogui.getActiveWindowTitle()
        captura_completa, captura_ventana = self.vision.capturar_pantalla(titulo_ventana)
        return captura_completa, captura_ventana

    def pensar(self, captura_completa: Image.Image, captura_ventana: Image.Image):
        self.logger.info("--- Fase: Pensar ---")
        if not self.objetivo:
            return {"tipo": "finalizar", "razon": "No hay objetivo"}

        # Consultar base de conocimiento (ejemplo simple)
        # En un caso real, se buscarían palabras clave del objetivo
        habilidad_conocida = self.kb.consultar_habilidad(self.objetivo)

        prompt = self._construir_prompt(habilidad_conocida)
        
        return self.llm_call(prompt, captura_completa, captura_ventana)

    def _construir_prompt(self, habilidad=None):
        # Base del prompt
        prompt_base = f"""
        Tu eres InteractIA, un agente de IA que controla un ordenador para cumplir un objetivo.
        Tu objetivo actual es: '{self.objetivo}'.
        
        Analiza las dos capturas de pantalla que se te proporcionan y decide la SIGUIENTE acción atómica y precisa a realizar para avanzar en el plan.
        Se te proporcionan dos imágenes:
        1.  **Captura de la ventana activa:** Esta es la vista principal y más importante, donde debes enfocar tu acción.
        2.  **Captura de la pantalla completa:** Úsala como contexto para entender la situación general si es necesario.

        Las acciones posibles son:
        - clic(x, y)
        - escribir(\"texto\")
        - abrir_app(\"app\")
        - presionar_tecla(\"tecla\") # ej. \"enter\", \"esc\"
        - scroll(\"direccion\", clics) #direccion puede ser 'arriba' o 'abajo'
        - arrastrar_barra(\"direccion\", porcentaje) # direccion puede ser 'vertical' o 'horizontal'
        - esperar(segundos)
        - finalizar(\"razón\")
        
        Devuelve tu decisión en formato JSON. Los parámetros de la acción deben estar anidados en un diccionario 'params'.
        Ejemplos de formato:
        - Para un clic: {{'accion': 'clic', 'params': {{'x': 120, 'y': 340}}}}
        - Para escribir: {{'accion': 'escribir', 'params': {{'texto': 'hola mundo'}}}}
        - Para abrir una app: {{'accion': 'abrir_app', 'params': {{'app': 'chrome.exe'}}}}
        - Para presionar Enter: {{'accion': 'presionar_tecla', 'params': {{'tecla': 'enter'}}}}
        - Para hacer scroll: {{'accion': 'scroll', 'params': {{'direccion': 'abajo', 'clics': 10}}}}
        - Para arrastrar la barra: {{'accion': 'arrastrar_barra', 'params': {{'direccion': 'vertical', 'porcentaje': 50}}}}
        
        Al usar `abrir_app`, asegúrate de incluir la extensión del programa (ej. `chrome.exe`).
        """

        # Construir el historial como una cadena de texto
        historial_str = "\n".join(map(str, self.historial_acciones[-5:])) if self.historial_acciones else "Ninguna"

        prompt_base = f"""
        Tu rol es InteractIA, un agente de IA que controla un ordenador.
        
        OBJETIVO ACTUAL: '{self.objetivo}'
        
        HISTORIAL DE ACCIONES RECIENTES (qué has hecho ya):
        {historial_str}
        
        PROCESO DE DECISIÓN:
        1.  **Tu única función es decidir la siguiente acción a tomar. Eres el único responsable de progresar en el objetivo. No asumas que nada ocurrirá si no lo ordenas explícitamente.**
        2.  **Antes de cada acción, asegúrate de que la ventana activa es la que esperas. Si no lo es, no realices ninguna acción y finaliza la tarea.**
        3.  **Antes de realizar cualquier acción, comprueba si la aplicación necesaria está abierta. Si no lo está, tu primera acción debe ser abrirla.**
        4.  **Cuando navegues a una URL, primero escribe la URL en la barra de direcciones, luego presiona 'enter' y espera a que la página se cargue completamente antes de realizar cualquier otra acción.**
        5.  **Recuerda que las ventanas pueden tener contenido que no se ve. Si no encuentras lo que buscas, puedes usar la acción `scroll` para desplazarte hacia arriba o hacia abajo. Para desplazamientos grandes y rápidos, es más eficiente usar `arrastrar_barra`. Observa la barra de desplazamiento para estimar cuánto contenido queda.**
        6.  **Para leer el contenido de una ventana, DEBES usar la acción `leer_texto_ventana_activa`. Esta es la única forma que tienes de saber qué texto hay en la pantalla. No des por hecho que el texto está leído hasta que no hayas usado esta acción y veas el resultado en el historial.**
        7.  Analiza el objetivo y el historial para determinar el siguiente paso lógico en el plan.
        8.  **Usa las dos capturas de pantalla para tomar tu decisión:**
            *   **Imagen 1 (Ventana Activa):** Enfócate en esta imagen para realizar acciones precisas como hacer clic o escribir.
            *   **Imagen 2 (Pantalla Completa):** Úsala para entender el contexto general si la ventana activa no es suficiente.
        9.  Devuelve ÚNICAMENTE la siguiente acción atómica en formato JSON, incluyendo el contexto esperado.
        
        ACCIONES DISPONIBLES:
        - clic(x, y)
        - escribir(\"texto\")
        - abrir_app(\"app\")
        - presionar_tecla(\"tecla\") # ej. \"enter\", \"esc\"
        - scroll(\"direccion\", clics) # Para desplazamientos finos
        - arrastrar_barra(\"direccion\", porcentaje) # Para desplazamientos grandes y rápidos. direccion: 'vertical' o 'horizontal', porcentaje: 0-100
        - finalizar(\"razón\")
        
        FORMATO DE RESPUESTA JSON:
        ```json
        {{
            "accion": "nombre_de_la_accion",
            "params": {{ "app": "valor" }},
            "contexto": {{ "titulo_ventana_contiene": "Parte del título de la ventana esperada" }}
        }}
        ```
        
        Ejemplo de razonamiento (no lo incluyas en la respuesta):
        - Objetivo: 'Abrir Notepad y escribir hola'. Historial: [abrir_app(notepad.exe)]. Pantalla: Notepad abierto.
        - Pensamiento: Notepad ya está abierto. El siguiente paso es escribir 'hola'. La ventana activa debe ser 'Notepad'.
        - Respuesta: {{'accion': 'escribir', 'params': {{'texto': 'hola'}}, 'contexto': {{'titulo_ventana_contiene': 'Notepad'}}}} 
        
        Ahora, proporciona la siguiente acción para tu objetivo actual.
        """;
        return prompt_base

    def llm_call(self, prompt: str, captura_completa: Image.Image, captura_ventana: Image.Image):
        self.logger.info("Enviando petición al modelo de IA...")
        try:
            contenido = [prompt]
            if captura_ventana:
                contenido.append(captura_ventana)
            contenido.append(captura_completa)

            respuesta = self.modelo.generate_content(contenido)
            
            # Limpiar y parsear la respuesta JSON
            json_text = respuesta.text.strip().replace('```json', '').replace('```', '')
            decision = json.loads(json_text)
            
            self.logger.info(f"Decisión recibida del modelo: {decision}")
            return decision
        except Exception as e:
            self.logger.error(f"ERROR al llamar al modelo de IA o parsear su respuesta: {e}")
            # En caso de error, intentar imprimir el feedback del prompt si está disponible
            if 'respuesta' in locals() and hasattr(respuesta, 'prompt_feedback'):
                self.logger.error(f"Contexto del Error (Feedback del Prompt): {respuesta.prompt_feedback}")
            return {"accion": "finalizar", "params": {"razon": "Error en el módulo de decisión"}}

    def actuar(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        contexto = decision.get("contexto")
        self.logger.info(f"--- Fase: Actuar ({accion}) ---")

        # --- GUARDIÁN DE SEGURIDAD ---
        if accion != "abrir_app" and contexto and "titulo_ventana_contiene" in contexto:
            titulo_esperado = contexto["titulo_ventana_contiene"]
            ventana_activa = pyautogui.getActiveWindowTitle()
            
            # Comprobación más flexible del título
            palabras_esperadas = set(titulo_esperado.lower().split())
            palabras_activas = set(ventana_activa.lower().split())

            if not palabras_esperadas.issubset(palabras_activas):
                error_msg = f"¡ERROR DE SEGURIDAD! La acción '{accion}' fue abortada. Ventana esperada: '{titulo_esperado}', Ventana activa: '{ventana_activa}'"
                self.logger.error(error_msg)
                return False # Detener el bucle por seguridad

        try:
            if accion == "clic":
                self.controlador.clic(params['x'], params['y'])
            elif accion == "escribir":
                self.controlador.escribir(params['texto'])
            elif accion == "abrir_app":
                self.controlador.abrir_aplicacion(params['app'])
            elif accion == "presionar_tecla":
                self.controlador.presionar_tecla(params['tecla'])
            elif accion == "scroll":
                self.controlador.scroll(params['direccion'], params['clics'])
            elif accion == "arrastrar_barra":
                self.controlador.arrastrar_barra(params['direccion'], params['porcentaje'])
            elif accion == "leer_texto_ventana_activa":
                texto_leido = self.vision.leer_texto_ventana_activa()
                self.historial_acciones.append({"accion": "leer_texto_ventana_activa", "resultado": texto_leido})
            elif accion == "esperar":
                self.controlador.esperar(params['segundos'])
            elif accion == "finalizar":
                return False # Indicar al bucle que debe terminar
            else:
                self.logger.warning(f"Acción desconocida: {accion}")
            
            if accion != "leer_texto_ventana_activa":
                self.historial_acciones.append(decision) # Guardar acción exitosa
            return True # Indicar al bucle que continúe
        except Exception as e:
            self.logger.error(f"ERROR al ejecutar la acción '{accion}': {e}")
            return False # Terminar en caso de error

    def run(self):
        if not self.operativo:
            self.logger.error("El agente no es operativo. Revisa la configuración y los errores.")
            return

        if not self.objetivo:
            self.logger.error("Error: No se ha establecido un objetivo.")
            return

        for i in range(10): # Límite de 10 ciclos para seguridad
            self.logger.info(f"--- Ciclo {i+1}/10 ---")
            captura_completa, captura_ventana = self.observar()
            decision = self.pensar(captura_completa, captura_ventana)
            
            if not self.actuar(decision):
                self.logger.info(f"Agente finalizando. Razón: {decision.get('params', {}).get('razon', 'Acción fallida o finalizada')}")
                break
            
            time.sleep(2)

if __name__ == '__main__':
    agente = Agente()
    if agente.operativo:
        # Guardar el nuevo conocimiento sobre las barras de desplazamiento
        agente.kb.guardar_habilidad(
            nombre_recurso="navegacion_ventana",
            tipo_recurso="Sistema Operativo",
            datos_habilidad={
                "descripcion": "Cómo navegar por contenido que no es visible en una ventana utilizando las barras de desplazamiento.",
                "acciones": [
                    {
                        "nombre": "arrastrar_barra",
                        "descripcion": "Arrastra la barra de desplazamiento vertical u horizontal para revelar otras partes del contenido.",
                        "parametros": {
                            "direccion": "'vertical' o 'horizontal'",
                            "porcentaje": "Un número de 0 a 100 que representa qué tan lejos mover la barra."
                        },
                        "cuando_usar": "Cuando se necesita hacer un desplazamiento grande y rápido por el contenido de una ventana."
                    },
                    {
                        "nombre": "scroll",
                        "descripcion": "Usa la rueda del ratón para desplazamientos pequeños y precisos.",
                        "cuando_usar": "Cuando se necesita hacer un ajuste fino en la vista actual."
                    }
                ],
                "heuristica": "La longitud de la barra de desplazamiento es proporcional a la cantidad de contenido visible. Una barra corta indica mucho contenido oculto. La posición de la barra indica la ubicación actual."
            }
        )

        agente.establecer_objetivo("Abre el Bloc de notas, escribe 'Hola, mundo!' y luego utiliza la herramienta de OCR para leer el texto y guardarlo en el historial.")
        agente.run()
