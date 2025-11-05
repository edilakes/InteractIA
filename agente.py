import json
import logging
import re

from comunicador import Comunicador
from memoria import MongoDBChatMemory
from model_manager import ModelProvider
from logger_config import setup_logging
from controlador import Controlador
from vision import capture_and_analyze_screen # Importar la función de visión

# El "Prompt Maestro" que define el comportamiento del agente
MASTER_PROMPT = """
Tu rol es InteractIA, un agente de IA experto en automatización de escritorio. Tu objetivo es ayudar al usuario controlando el teclado y el ratón para realizar tareas. Analiza la petición del usuario y el contexto proporcionado para decidir tu próximo paso.

CONTEXTO DE LA CONVERSACIÓN:
{historial_chat}

ANÁLISIS DE LA PANTALLA:
{analisis_pantalla}

INFORMACIÓN DE LA BASE DE CONOCIMIENTO:
{info_conocimiento}

TAREA ACTUAL DEL USUARIO: "{user_message}"

DEBES responder ÚNICAMENTE con un objeto JSON que represente tu próxima acción. La estructura debe ser la siguiente:

{
  "accion": "<nombre_de_la_accion>",
  "argumentos": {
    "param1": "valor1",
    ...
  }
}

ACCIONES DISPONIBLES:
**Acciones Primitivas (Controlador):**
- `mover_raton(x, y, duracion=1)`
- `escribir(texto, intervalo=0.05)`
- `clic(x=None, y=None, boton='left')`
- `presionar_tecla(tecla)`
- `scroll(clics)`
- `esperar(segundos)`

**Acciones Compuestas (Orquestador):**
- `navegar_a_url(url)`: Abre el navegador y navega a la URL especificada.
- `buscar_en_google(termino_busqueda)`: Realiza una búsqueda en Google.

**Acciones Internas:**
- `responder_chat(mensaje)`: Envía un mensaje al usuario.
- `analizar_pantalla()`: Realiza un análisis del entorno visual y actualiza el contexto.
- `consultar_base_conocimiento(termino_busqueda)`: Busca en la base de conocimiento y actualiza el contexto.
- `finalizar_tarea(mensaje_final)`: Indica que la tarea ha sido completada.

Elige la acción más lógica para avanzar hacia la solución de la tarea del usuario.
"""

class Agente:
    def __init__(self, model_provider: ModelProvider, model_name: str, callback_hablar=None):
        self.comunicador = Comunicador(callback_hablar=callback_hablar)
        setup_logging(comunicador=self.comunicador)
        self.logger = logging.getLogger("InteractIA")
        self.logger.info("Inicializando Agente...")

        self.model_provider = model_provider
        self.model_provider.set_model(model_name)
        
        self.memoria = MongoDBChatMemory(model_provider=self.model_provider)
        self.controlador = Controlador()
        self.vision_analysis = "No se ha realizado ningún análisis de pantalla aún."
        self.kb_info = "No se ha consultado la base de conocimiento aún."

    def _limpiar_y_parsear_json(self, texto_respuesta: str) -> dict:
        self.logger.debug(f"Limpiando texto para JSON: '{texto_respuesta}'")
        match = re.search(r'```json\s*(\{.*?\})\s*```', texto_respuesta, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = texto_respuesta.find('{')
            end = texto_respuesta.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = texto_respuesta[start:end+1]
            else:
                json_str = texto_respuesta
        json_str = json_str.replace("'", '"')
        self.logger.debug(f"Contenido de json_str antes de parsear: {json_str}")
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar JSON: {e}. Contenido: '{json_str}'")
            return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno: no pude procesar mi propia decisión. ({e})"}}

    def _query_llm(self, prompt: str) -> dict:
        self.logger.info("Enviando petición al modelo de IA...")
        try:
            respuesta_bruta = self.model_provider.generate_content(prompt)
            self.logger.debug(f"Respuesta BRUTA del modelo: {respuesta_bruta}")
            
            texto_para_parsear = respuesta_bruta if isinstance(respuesta_bruta, str) else respuesta_bruta.get('text', str(respuesta_bruta))
            
            if not texto_para_parsear:
                raise ValueError("La respuesta del modelo está vacía.")

            return self._limpiar_y_parsear_json(texto_para_parsear)

        except Exception as e:
            self.logger.error(f"ERROR al llamar al proveedor del modelo de IA: {e}", exc_info=True)
            return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno: no pude contactar con el modelo de IA. ({e})"}}

    def _ejecutar_accion_primitiva(self, accion: str, args: dict):
        self.logger.info(f"Ejecutando acción primitiva: {accion} con args: {args}")
        try:
            if hasattr(self.controlador, accion):
                method = getattr(self.controlador, accion)
                return method(**args)
            else:
                return f"Acción primitiva desconocida: {accion}"
        except Exception as e:
            self.logger.error(f"Error ejecutando acción primitiva '{accion}': {e}", exc_info=True)
            return f"Error en '{accion}': {e}"

    def _ejecutar_accion_compuesta(self, accion: str, args: dict):
        self.logger.info(f"Ejecutando acción compuesta: {accion} con args: {args}")
        if accion == "navegar_a_url":
            url = args.get("url")
            if not url:
                return "Error: La URL no fue proporcionada para navegar."
            self.controlador.presionar_tecla("win+r")
            self.controlador.esperar(1)
            self.controlador.escribir("chrome")
            self.controlador.presionar_tecla("enter")
            self.controlador.esperar(2)
            self.controlador.escribir(url)
            self.controlador.presionar_tecla("enter")
            return f"Navegación a {url} completada."
        
        elif accion == "buscar_en_google":
            termino = args.get("termino_busqueda")
            if not termino:
                return "Error: El término de búsqueda no fue proporcionado."
            self.controlador.presionar_tecla("win+r")
            self.controlador.esperar(1)
            self.controlador.escribir("chrome")
            self.controlador.presionar_tecla("enter")
            self.controlador.esperar(2)
            self.controlador.escribir(f"https://www.google.com/search?q={termino.replace(' ', '+')}")
            self.controlador.presionar_tecla("enter")
            return f"Búsqueda de '{termino}' en Google completada."
            
        return None # Indica que no es una acción compuesta conocida

    def run_cycle(self, user_message: str, session_id: str):
        self.logger.info(f"--- Iniciando ciclo para mensaje: '{user_message}' ---")

        # 1. Recopilar contexto
        historial_raw = self.memoria._recuperar_historial_crudo(session_key=session_id)
        historial_chat = self.memoria.convertir_historial_a_formato_simple(historial_raw)
        
        # 2. Construir el prompt
        prompt = MASTER_PROMPT.format(
            historial_chat="\n".join([f"{msg['rol']}: {msg['contenido']}" for msg in historial_chat]),
            analisis_pantalla=self.vision_analysis,
            info_conocimiento=self.kb_info,
            user_message=user_message
        )

        # 3. Consultar al LLM
        decision_json = self._query_llm(prompt)
        accion = decision_json.get("accion")
        argumentos = decision_json.get("argumentos", {})
        
        self.logger.info(f"Acción decidida por el LLM: {accion}")

        if not accion:
            resultado = "El modelo no especificó una acción a realizar."
            self.comunicador.hablar(resultado)
        else:
            resultado = self._ejecutar_accion_compuesta(accion, argumentos)
            
            if resultado is None: # No era una acción compuesta
                # Intentar como acción interna o primitiva
                if accion == "responder_chat":
                    self.comunicador.hablar(argumentos.get("mensaje", "No tengo nada que decir."))
                    resultado = "Mensaje enviado al usuario."
                elif accion == "finalizar_tarea":
                    self.comunicador.hablar(f"Tarea finalizada: {argumentos.get('mensaje_final', 'Completado.')}")
                    resultado = "Tarea marcada como finalizada."
                elif accion == "analizar_pantalla":
                    self.vision_analysis = capture_and_analyze_screen()
                    self.comunicador.hablar("Análisis de pantalla realizado y contexto actualizado.")
                    resultado = "Análisis de pantalla completado."
                elif accion == "consultar_base_conocimiento":
                    termino = argumentos.get("termino_busqueda")
                    if termino:
                        self.kb_info = self.memoria.query_base_conocimiento(termino)
                        self.comunicador.hablar("Consulta a la base de conocimiento realizada y contexto actualizado.")
                        resultado = "Consulta a la KB completada."
                    else:
                        resultado = "Error: No se proporcionó término de búsqueda para la KB."
                else:
                    resultado = self._ejecutar_accion_primitiva(accion, argumentos)
            
            self.logger.info(f"Resultado de la acción '{accion}': {resultado}")
            if accion not in ["responder_chat", "finalizar_tarea", "analizar_pantalla", "consultar_base_conocimiento"]:
                 self.comunicador.hablar(f"Acción '{accion}' ejecutada.")

        self.memoria.guardar_mensaje(session_id, 'usuario', {'texto': user_message})
        self.memoria.guardar_mensaje(session_id, 'agente', {'accion': accion, 'argumentos': argumentos, 'resultado': resultado})

        self.logger.info("--- Fin del ciclo ---")

if __name__ == '__main__':
    print("Este es el nuevo agente. No contiene un bloque de prueba principal.")