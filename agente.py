import json
import logging
import re
import ast

from comunicador import Comunicador
from memoria import MongoDBChatMemory
from model_manager import ModelProvider
from logger_config import setup_logging
from controlador import Controlador
from vision import capture_and_analyze_screen # Importar la función de visión

# El "Prompt Maestro" que define el comportamiento del agente
MASTER_PROMPT_TEMPLATE = """
Tu rol es InteractIA, un agente de IA experto en automatización de escritorio. Tu objetivo es ayudar al usuario controlando el teclado y el ratón para realizar tareas. Analiza la petición del usuario y el contexto proporcionado para decidir tu próximo paso.

CONTEXTO DE LA CONVERSACIÓN:
{historial_chat}

ANÁLISIS DE LA PANTALLA:
{analisis_pantalla}

INFORMACIÓN DE LA BASE DE CONOCIMIENTO:
{info_conocimiento}

TAREA ACTUAL DEL USUARIO: "{user_message}"

DEBES responder ÚNICAMENTE con un objeto JSON que represente tu próxima acción. La estructura debe ser la siguiente:
"""

JSON_ACTION_EXAMPLE = """
{
  "accion": "<nombre_de_la_accion>",
  "argumentos": {
    "param1": "valor1",
    ...
  }
}
"""

MASTER_PROMPT_ACTIONS = """
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
- `responder_chat(mensaje)`: Envía un mensaje al usuario. **Úsala cuando la tarea esté completamente terminada o necesites una aclaración del usuario.**
- `analizar_pantalla()`: Realiza un análisis del entorno visual y actualiza el contexto.
- `consultar_base_conocimiento(termino_busqueda)`: Busca en la base de conocimiento y actualiza el contexto.
- `finalizar_tarea(mensaje_final)`: Indica que la tarea ha sido completada. **Úsala solo cuando la tarea del usuario esté 100% resuelta y no haya más pasos pendientes.**

Elige la acción más lógica para avanzar hacia la solución de la tarea del usuario. Si la tarea requiere múltiples pasos, elige la siguiente acción necesaria. No finalices la tarea prematuramente.
"""

# Descripción del esquema JSON esperado para la auto-corrección del LLM
EXPECTED_JSON_SCHEMA_DESCRIPTION = """
El JSON debe tener la siguiente estructura:
{
  "accion": "string", // El nombre de la acción a ejecutar
  "argumentos": { // Un objeto con los argumentos para la acción
    "param1": "valor1",
    // ... otros parámetros según la acción
  }
}
Asegúrate de que todas las claves y valores de cadena estén entre comillas dobles.
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

    def _generar_prompt_correccion(self, malformed_response: str, error_message: str) -> str:
        return f"""
        Tu respuesta anterior no pudo ser parseada correctamente como JSON. \n"""
        f"""El error fue: {error_message}\n"""
        f"""Tu respuesta original fue:\n```\n{malformed_response}\n```\n"""
        f"""Por favor, corrige tu respuesta para que sea un JSON válido y se ajuste al siguiente esquema:\n"""
        f"""{EXPECTED_JSON_SCHEMA_DESCRIPTION}\n"""
        f"""Responde ÚNICAMENTE con el objeto JSON corregido, sin texto adicional ni explicaciones.\n"""

    def _parsear_respuesta_llm_con_correccion(self, raw_llm_response_text: str, max_retries: int = 3) -> dict:
        current_response_text = raw_llm_response_text
        for retry_count in range(max_retries):
            self.logger.debug(f"Intento de parseo JSON {retry_count + 1}/{max_retries}: '{current_response_text}'")
            
            json_str = current_response_text
            # Limpieza: intentar extraer JSON de bloques de markdown o de la cadena completa
            match = re.search(r'```json\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Intentar encontrar el JSON más externo si no hay bloque markdown
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1 and start < end:
                    json_str = json_str[start:end+1]
                # Si no se encuentra un bloque JSON claro, se asume que toda la respuesta es el JSON
            
            parsed_json = None
            error_message = ""

            # Intento 1: Parsear como JSON estándar
            try:
                parsed_json = json.loads(json_str)
            except json.JSONDecodeError as e:
                error_message = f"Error al decodificar JSON estándar: {e}"
                self.logger.debug(f"{error_message}. Contenido: '{json_str}'")
                
                # Intento 2: Si falla, intentar parsear como literal de Python y luego convertir a JSON
                try:
                    # para que ast.literal_eval lo interprete correctamente
                    # y luego json.dumps lo vuelva a escapar si es necesario.
                    # Esto es crucial para manejar las respuestas del LLM que a veces usan \n
                    cleaned_json_str = json_str.replace('\\n', '\n')
                    python_literal = ast.literal_eval(cleaned_json_str)
                    # Convertir el literal de Python a una cadena JSON válida
                    parsed_json = json.loads(json.dumps(python_literal))
                    self.logger.debug("Parseado exitoso como literal de Python y convertido a JSON.")
                except (SyntaxError, ValueError, TypeError) as e_literal:
                    error_message = f"Error al decodificar como literal de Python: {e_literal}"
                    self.logger.debug(f"{error_message}. Contenido: '{json_str}'")
                    
                    # Intento 3: Heurística de reemplazar comillas simples por dobles y reintentar json.loads
                    try:
                        # Solo aplicar esta heurística si los intentos anteriores fallaron
                        json_str_fixed_quotes = json_str.replace("'", '"')
                        parsed_json = json.loads(json.dumps(json_str_fixed_quotes))
                        self.logger.debug("Parseado exitoso con reemplazo de comillas simples.")
                    except json.JSONDecodeError as e_final:
                        error_message = f"Error final al decodificar JSON con comillas corregidas: {e_final}"
                        self.logger.warning(f"{error_message}. Contenido: '{json_str_fixed_quotes}'")

            if parsed_json:
                # Validar el esquema básico
                if isinstance(parsed_json, dict) and "accion" in parsed_json and "argumentos" in parsed_json:
                    self.logger.info(f"JSON parseado y validado exitosamente en intento {retry_count + 1}.")
                    return parsed_json
                else:
                    error_message = "El JSON no contiene las claves 'accion' y 'argumentos' o no es un diccionario válido."
                    self.logger.warning(f"Validación de esquema fallida: {error_message}")
            
            # Si llegamos aquí, el parseo o la validación fallaron
            if retry_count < max_retries - 1:
                self.logger.info(f"Intentando auto-corrección del LLM (intento {retry_count + 1})...")
                correction_prompt = self._generar_prompt_correccion(current_response_text, error_message)
                new_llm_response = self.model_provider.generate_content(correction_prompt)
                current_response_text = new_llm_response if isinstance(new_llm_response, str) else new_llm_response.get('text', str(new_llm_response))
                if not current_response_text:
                    self.logger.error("El LLM devolvió una respuesta vacía durante la corrección.")
                    break # Salir del bucle si la corrección es vacía
            else:
                self.logger.error(f"Falló el parseo JSON después de {max_retries} intentos. Último error: {error_message}")
                # Retornar una acción de error si todos los reintentos fallan
                return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno: no pude procesar la decisión del modelo después de {max_retries} intentos. ({error_message})"}}
        
        # Esto solo se alcanzará si el bucle termina sin éxito y sin retornar en el último intento
        return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno desconocido durante el parseo de la respuesta del modelo."}}

    def _query_llm(self, prompt: str) -> dict:
        self.logger.info("Enviando petición al modelo de IA...")
        try:
            respuesta_bruta = self.model_provider.generate_content(prompt)
            self.logger.debug(f"Respuesta BRUTA del modelo: {respuesta_bruta}")
            
            texto_para_parsear = respuesta_bruta if isinstance(respuesta_bruta, str) else respuesta_bruta.get('text', str(respuesta_bruta))
            
            if not texto_para_parsear:
                raise ValueError("La respuesta del modelo está vacía.")

            return self._parsear_respuesta_llm_con_correccion(texto_para_parsear, max_retries=3)

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

    def _run_single_cycle(self, user_message: str, session_id: str) -> str:
        self.logger.info(f"--- Iniciando ciclo para mensaje: '{user_message}' ---")

        # 1. Recopilar contexto
        historial_raw = self.memoria._recuperar_historial_crudo(session_key=session_id)
        historial_chat = self.memoria.convertir_historial_a_formato_simple(historial_raw)
        
        # 2. Construir el prompt
        prompt = MASTER_PROMPT_TEMPLATE.format(
            historial_chat="\n".join([f"{msg['rol']}: {msg['contenido']}" for msg in historial_chat]),
            analisis_pantalla=self.vision_analysis,
            info_conocimiento=self.kb_info,
            user_message=user_message
        )
        prompt += JSON_ACTION_EXAMPLE
        prompt += MASTER_PROMPT_ACTIONS

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
        return accion # Return the action taken

    def execute_task(self, initial_user_message: str, session_id: str):
        current_message = initial_user_message
        task_completed = False
        max_task_cycles = 10 # Prevent infinite loops
        cycle_count = 0

        while not task_completed and cycle_count < max_task_cycles:
            cycle_count += 1
            self.logger.info(f"--- Ejecutando ciclo de tarea {cycle_count}/{max_task_cycles} ---")
            
            # Execute a single cycle of the agent
            accion_ejecutada = self._run_single_cycle(current_message, session_id)

            # Determine if the task is completed based on the action executed
            if accion_ejecutada in ["responder_chat", "finalizar_tarea"]:
                task_completed = True
                self.logger.info(f"Tarea finalizada por acción: {accion_ejecutada}")
            else:
                # For multi-step tasks, the agent needs to decide the next step.
                # The 'current_message' for the next cycle should reflect the ongoing task.
                # For now, we'll keep it as the initial message, but this might need refinement
                # if the LLM needs to be prompted with updated context for the *next* step.
                # A more advanced approach would be to have the LLM generate the 'next_step_message'.
                self.logger.info(f"La tarea continúa. Acción ejecutada: {accion_ejecutada}")
                # Optionally, update current_message based on the result of the last action
                # For now, we rely on the LLM's ability to use chat history and screen analysis.

        if not task_completed:
            self.logger.warning(f"La tarea no se completó después de {max_task_cycles} ciclos.")
            self.comunicador.hablar(f"No pude completar la tarea después de {max_task_cycles} intentos. Por favor, intenta de nuevo o sé más específico.")


if __name__ == '__main__':
    print("Este es el nuevo agente. No contiene un bloque de prueba principal.")