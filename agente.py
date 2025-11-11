import json
import logging
import re
import ast
from enum import Enum

from comunicador import Comunicador
from memoria import MongoDBChatMemory
from model_manager import ModelProvider
from logger_config import setup_logging
from controlador import Controlador
from vision import capture_and_analyze_screen
from considerations_db_manager import considerations_db_manager
import grabador
from utils import wait_for_condition
from verificador import Verificador

# Define los estados posibles del agente
class AgentState(Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING_ACTION = "EXECUTING_ACTION"
    VERIFYING_ACTION = "VERIFYING_ACTION"
    WAITING_FOR_USER_INPUT = "WAITING_FOR_USER_INPUT"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    DEMONSTRATING = "DEMONSTRATING"

# El "Prompt Maestro" que define el comportamiento del agente
MASTER_PROMPT_TEMPLATE = """
Tu rol es InteractIA, un agente de IA experto en automatización de escritorio. Tu objetivo es ayudar al usuario controlando el teclado y el ratón para realizar tareas. Analiza la petición del usuario y el contexto proporcionado para decidir tu próximo paso.

CONTEXTO DE LA CONVERSACIÓN:
{historial_chat}

ANÁLISIS DE LA PANTALLA:
{analisis_pantalla}

INFORMACIÓN DE LA BASE DE CONOCIMIENTO:
{info_conocimiento}

CONSIDERACIONES ADICIONALES:
{consideraciones_adicionales}

TAREA ACTUAL DEL USUARIO: \"{user_message}\" 

DEBES responder ÚNICAMENTE con un objeto JSON que represente tu próxima acción. La estructura debe ser la siguiente:
"""

JSON_ACTION_EXAMPLE = """
{
  "accion": "<nombre_de_la_accion>",
  "argumentos": {
    "param1": "valor1",
    ...
  },
  "confidence_score": 0.95,
  "explanation": "Breve explicación de por qué se eligió esta acción.",
  "expected_outcome": "Descripción detallada de cómo debería verse la pantalla después de ejecutar la acción. Por ejemplo, 'La calculadora de Windows debería estar abierta y visible en la pantalla'."
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
- `responder_chat(mensaje)`: Envía un mensaje al usuario.
- `analizar_pantalla()`: Realiza un análisis del entorno visual y actualiza el contexto.
- `consultar_base_conocimiento(termino_busqueda)`: Busca en la base de conocimiento y actualiza el contexto.
- `finalizar_tarea(mensaje_final)`: Indica que la tarea ha sido completada.
- `tarea_completada()`: Indica que la tarea ha sido resuelta.

Elige la acción más lógica para avanzar hacia la solución de la tarea del usuario.
"""

EXPECTED_JSON_SCHEMA_DESCRIPTION = """
El JSON debe tener la siguiente estructura:
{
  "accion": "string",
  "argumentos": {
    "param1": "valor1",
  },
  "confidence_score": float,
  "explanation": "string",
  "expected_outcome": "string"
}
Asegúrate de que todas las claves y valores de cadena estén entre comillas dobles.
"""

LESSON_GENERATION_PROMPT_SUCCESS = """
La acción "{accion}" con argumentos {argumentos} fue exitosa. El estado actual de la pantalla es:
{analisis_pantalla}
Basado en este éxito, genera una lección concisa para el futuro.
Responde ÚNICAMENTE con un objeto JSON con las claves "nombre_leccion" y "contenido_leccion".
"""

LESSON_GENERATION_PROMPT_FAILURE = """
La acción "{accion}" con argumentos {argumentos} falló. El estado actual de la pantalla es:
{analisis_pantalla}
Basado en este fracaso, genera una lección concisa para el futuro.
Responde ÚNICAMENTE con un objeto JSON con las claves "nombre_leccion" y "contenido_leccion".
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
        self.verificador = Verificador(model_provider=self.model_provider)
        self.vision_analysis = "No se ha realizado ningún análisis de pantalla aún."
        self.kb_info = "No se ha consultado la base de conocimiento aún."
        self._stop_requested = False
        self.state = AgentState.IDLE

    def request_stop(self):
        self.logger.info("Solicitud de detención recibida.")
        self._stop_requested = True

    def _generar_prompt_correccion(self, malformed_response: str, error_message: str) -> str:
        return f"""
        Tu respuesta anterior no pudo ser parseada correctamente como JSON. 
        El error fue: {error_message}
        Tu respuesta original fue:
        ```
        {malformed_response}
        ```
        Por favor, corrige tu respuesta para que sea un JSON válido y se ajuste al siguiente esquema:
        {EXPECTED_JSON_SCHEMA_DESCRIPTION}
        Responde ÚNICAMENTE con el objeto JSON corregido, sin texto adicional ni explicaciones.
"""

    def _parsear_respuesta_llm_con_correccion(self, raw_llm_response_text: str, max_retries: int = 3) -> dict:
        current_response_text = raw_llm_response_text
        for retry_count in range(max_retries):
            self.logger.debug(f"Intento de parseo JSON {retry_count + 1}/{max_retries}: '{{current_response_text}}'")
            
            json_str = current_response_text
            match = re.search(r'```json\s*(\{.*?\})\s*```', json_str, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1 and start < end:
                    json_str = json_str[start:end+1]
            
            parsed_json = None
            error_message = ""

            try:
                json_str_fixed_keys = re.sub(r"([{,]\s*)\'([^']+?)\'", r"\1\"\2\"", json_str)
                parsed_json = json.loads(json_str_fixed_keys)
            except json.JSONDecodeError as e:
                error_message = f"Error al decodificar JSON: {{e}}"

            if not parsed_json:
                try:
                    parsed_json = json.loads(json_str)
                except json.JSONDecodeError as e:
                    error_message = f"Error al decodificar JSON: {{e}}"
                    try:
                        cleaned_json_str = json_str.replace('\\n', '\n')
                        python_literal = ast.literal_eval(cleaned_json_str)
                        parsed_json = json.loads(json.dumps(python_literal))
                    except (SyntaxError, ValueError, TypeError) as e_literal:
                        error_message = f"Error al decodificar como literal de Python: {{e_literal}}"
                        try:
                            json_str_fixed_quotes = json_str.replace("'", '"')
                            parsed_json = json.loads(json_str_fixed_quotes)
                        except json.JSONDecodeError as e_final:
                            error_message = f"Error final al decodificar JSON: {{e_final}}"

            if parsed_json:
                is_action_decision = isinstance(parsed_json, dict) and "accion" in parsed_json and "argumentos" in parsed_json and "expected_outcome" in parsed_json
                is_lesson_response = isinstance(parsed_json, dict) and "nombre_leccion" in parsed_json and "contenido_leccion" in parsed_json

                if is_action_decision or is_lesson_response:
                    self.logger.info(f"JSON parseado y validado exitosamente en intento {{retry_count + 1}}.")
                    return parsed_json
                else:
                    error_message = "El JSON no contiene las claves esperadas."
            
            if retry_count < max_retries - 1:
                self.logger.info(f"Intentando auto-corrección del LLM (intento {{retry_count + 1}})...")
                correction_prompt = self._generar_prompt_correccion(current_response_text, error_message)
                new_llm_response = self.model_provider.generate_content(correction_prompt)
                current_response_text = new_llm_response if isinstance(new_llm_response, str) else new_llm_response.get('text', str(new_llm_response))
                if not current_response_text:
                    self.logger.error("El LLM devolvió una respuesta vacía durante la corrección.")
                    break
            else:
                self.logger.error(f"Falló el parseo JSON después de {max_retries} intentos. Último error: {{error_message}}")
                return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno: no pude procesar la decisión del modelo después de {max_retries} intentos. ({{error_message}})"}}
        
        return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno desconocido durante el parseo de la respuesta del modelo."}}

    def _handle_low_confidence_interaction(self, accion: str, argumentos: dict, confidence_score: float, explanation: str, user_message: str) -> dict:
        self.comunicador.hablar(f"No estoy muy seguro de cómo proceder con la acción '{{accion}}'.")
        self.comunicador.hablar(f"Mi confianza es del {confidence_score:.0%}. Explicación: {{explanation}}")
        self.comunicador.hablar("¿Qué te gustaría hacer?")
        self.comunicador.hablar("[P]roceder, [C]orregir, [M]ostrarme")

        while True:
            user_choice = input("Tu elección (P/C/M): ").strip().upper()
            if user_choice == 'P':
                return {"decision": "proceder"}
            elif user_choice == 'C':
                new_instructions = input("Nuevas instrucciones: ").strip()
                if new_instructions:
                    return {"decision": "corregir", "new_message": new_instructions}
            elif user_choice == 'M':
                return {"decision": "demostrar"}

    def _query_llm(self, prompt: str) -> dict:
        self.logger.info("Enviando petición al modelo de IA...")
        try:
            respuesta_bruta = self.model_provider.generate_content(prompt)
            texto_para_parsear = respuesta_bruta if isinstance(respuesta_bruta, str) else respuesta_bruta.get('text', str(respuesta_bruta))
            if not texto_para_parsear:
                raise ValueError("La respuesta del modelo está vacía.")
            return self._parsear_respuesta_llm_con_correccion(texto_para_parsear)
        except Exception as e:
            self.logger.error(f"ERROR al llamar al proveedor del modelo de IA: {{e}}", exc_info=True)
            return {"accion": "responder_chat", "argumentos": {"mensaje": f"Error interno: no pude contactar con el modelo de IA."}}

    def _ejecutar_accion_primitiva(self, accion: str, args: dict):
        self.logger.info(f"Ejecutando acción primitiva: {accion} con args: {args}")
        try:
            if hasattr(self.controlador, accion):
                method = getattr(self.controlador, accion)
                return method(**args)
            else:
                return f"Acción primitiva desconocida: {accion}"
        except Exception as e:
            self.logger.error(f"Error ejecutando acción primitiva '{accion}': {{e}}", exc_info=True)
            return f"Error en '{accion}': {{e}}"

    def _ejecutar_accion_compuesta(self, accion: str, args: dict):
        self.logger.info(f"Ejecutando acción compuesta: {accion} con args: {args}")
        if accion == "navegar_a_url":
            url = args.get("url")
            self.controlador.presionar_tecla("win+r")
            wait_for_condition("window_open", "Google Chrome", timeout=5)
            self.controlador.escribir("chrome")
            self.controlador.presionar_tecla("enter")
            wait_for_condition("window_open", "Google Chrome", timeout=5)
            self.controlador.escribir(url)
            self.controlador.presionar_tecla("enter")
            return f"Navegación a {url} completada."
        elif accion == "buscar_en_google":
            termino = args.get("termino_busqueda")
            self.controlador.presionar_tecla("win+r")
            wait_for_condition("window_open", "Google Chrome", timeout=5)
            self.controlador.escribir("chrome")
            self.controlador.presionar_tecla("enter")
            wait_for_condition("window_open", "Google Chrome", timeout=5)
            self.controlador.escribir(f"https://www.google.com/search?q={termino.replace(' ', '+')}")
            self.controlador.presionar_tecla("enter")
            return f"Búsqueda de '{termino}' en Google completada."
        return None

    def _load_additional_considerations(self) -> str:
        try:
            considerations = considerations_db_manager.get_all_considerations()
            if not considerations:
                return "No hay consideraciones adicionales."
            return "\n".join([f"- {c['nombre']}: {c['contenido']}" for c in considerations])
        except Exception as e:
            self.logger.error(f"Error al cargar consideraciones adicionales: {{e}}", exc_info=True)
            return "Error al cargar las consideraciones adicionales."

    def _verify_and_learn(self, accion: str, argumentos: dict, pre_screenshot: str, pre_mouse_pos: dict, expected_outcome: str):
        self.state = AgentState.VERIFYING_ACTION
        self.logger.info(f"Verificando la acción '{accion}'...")
        
        post_screenshot = self.controlador.capturar_pantalla()
        
        verification_result = self.verificador.verificar_accion(
            accion, 
            argumentos, 
            pre_screenshot, 
            post_screenshot, 
            expected_outcome=expected_outcome,
            mouse_pos=pre_mouse_pos
        )
        
        is_verified = verification_result.get("verificado", False)
        confidence = verification_result.get("confianza", 0.0)
        explanation = verification_result.get("razon", "No se proporcionó explicación.")

        if confidence < 0.9:
            self.logger.warning(f"Confianza de verificación baja ({{confidence:.2f}}). Pidiendo confirmación al usuario.")
            self.comunicador.hablar(f"Creo que la acción '{accion}' {{'tuvo éxito' if is_verified else 'falló'}}. Razón: {{explanation}}")
            user_feedback = input("¿Es esto correcto? (S/N): ").strip().upper()
            if user_feedback == 'S':
                final_is_verified = is_verified
            else:
                final_is_verified = not is_verified
        else:
            final_is_verified = is_verified

        self._generate_lesson(accion, argumentos, final_is_verified, post_screenshot)

        if final_is_verified:
            self.logger.info(f"Acción '{accion}' verificada exitosamente.")
        else:
            self.logger.warning(f"La acción '{accion}' falló.")

        self.state = AgentState.PLANNING

    def _generate_lesson(self, accion: str, argumentos: dict, fue_exitoso: bool, screen_analysis: str):
        self.logger.info(f"Generando lección para la acción '{accion}' que {{'tuvo éxito' if fue_exitoso else 'falló'}}.")
        prompt_template = LESSON_GENERATION_PROMPT_SUCCESS if fue_exitoso else LESSON_GENERATION_PROMPT_FAILURE
        lesson_prompt = prompt_template.format(accion=accion, argumentos=json.dumps(argumentos), analisis_pantalla=screen_analysis)
        lesson_response = self._query_llm(lesson_prompt)
        lesson_name = lesson_response.get("nombre_leccion")
        lesson_content = lesson_response.get("contenido_leccion")
        if lesson_name and lesson_content:
            try:
                considerations_db_manager.add_consideration(lesson_name, lesson_content)
                self.logger.info(f"Nueva consideración guardada: '{lesson_name}'")
            except Exception as e:
                self.logger.error(f"Error al guardar la consideración: {{e}}")

    def _run_single_cycle(self, user_message: str, session_id: str) -> str:
        if self._stop_requested:
            return "stopped"
        self.logger.info(f"--- Iniciando ciclo para mensaje: '{user_message}' ---")

        historial_raw = self.memoria._recuperar_historial_crudo(session_id)
        historial_chat = self.memoria.convertir_historial_a_formato_simple(historial_raw)
        additional_considerations = self._load_additional_considerations()
        
        prompt = MASTER_PROMPT_TEMPLATE.format(
            historial_chat="\n".join([f"{msg['rol']}: {msg['contenido']}" for msg in historial_chat]),
            analisis_pantalla=self.vision_analysis,
            info_conocimiento=self.kb_info,
            consideraciones_adicionales=additional_considerations,
            user_message=user_message
        )
        prompt += JSON_ACTION_EXAMPLE
        prompt += MASTER_PROMPT_ACTIONS

        decision_json = self._query_llm(prompt)
        accion = decision_json.get("accion")
        argumentos = decision_json.get("argumentos", {})
        confidence_score = decision_json.get("confidence_score", 0.0)
        explanation = decision_json.get("explanation", "No se proporcionó explicación.")
        expected_outcome = decision_json.get("expected_outcome", "No se proporcionó una descripción del resultado esperado.")
        
        self.logger.info(f"Acción decidida por el LLM: {accion} (Confianza: {confidence_score:.2f})")

        if confidence_score < 0.8:
            interaction_result = self._handle_low_confidence_interaction(accion, argumentos, confidence_score, explanation, user_message)
            if interaction_result["decision"] == "corregir":
                return self._run_single_cycle(interaction_result["new_message"], session_id)
            elif interaction_result["decision"] == "demostrar":
                return "demostrar_accion"

        if not accion:
            resultado = "El modelo no especificó una acción a realizar."
        else:
            pre_screenshot = self.controlador.capturar_pantalla()
            pre_mouse_pos = self.controlador.obtener_posicion_raton()
            resultado = self._ejecutar_accion_compuesta(accion, argumentos)
            
            if resultado is None:
                if accion == "responder_chat":
                    self.comunicador.hablar(argumentos.get("mensaje", ""))
                    resultado = "Mensaje enviado."
                elif accion == "finalizar_tarea":
                    self.comunicador.hablar(argumentos.get('mensaje_final', 'Completado.'))
                    resultado = "Tarea finalizada."
                elif accion == "analizar_pantalla":
                    self.vision_analysis = capture_and_analyze_screen()
                    resultado = "Análisis de pantalla completado."
                elif accion == "consultar_base_conocimiento":
                    termino = argumentos.get("termino_busqueda")
                    self.kb_info = self.memoria.query_base_conocimiento(termino)
                    resultado = "Consulta a la KB completada."
                elif accion == "tarea_completada":
                    resultado = "Tarea completada."
                else:
                    resultado = self._ejecutar_accion_primitiva(accion, argumentos)
            
            self.logger.info(f"Resultado de la acción '{accion}': {resultado}")
            if accion not in ["responder_chat", "finalizar_tarea", "analizar_pantalla", "consultar_base_conocimiento", "tarea_completada"]:
                 self._verify_and_learn(accion, argumentos, pre_screenshot, pre_mouse_pos, expected_outcome)

        self.memoria.guardar_mensaje(session_id, 'usuario', {'texto': user_message})
        self.memoria.guardar_mensaje(session_id, 'agente', {'accion': accion, 'argumentos': argumentos, 'resultado': resultado})

        return accion

    def execute_task(self, initial_user_message: str, session_id: str):
        current_message = initial_user_message
        task_completed = False
        max_task_cycles = 1
        cycle_count = 0

        self.state = AgentState.PLANNING

        while not task_completed and cycle_count < max_task_cycles and not self._stop_requested:
            cycle_count += 1
            self.state = AgentState.EXECUTING_ACTION
            accion_ejecutada = self._run_single_cycle(current_message, session_id)

            if self._stop_requested:
                task_completed = True
                self.state = AgentState.TASK_FAILED
            elif accion_ejecutada == "demostrar_accion":
                self.state = AgentState.DEMONSTRATING
                grabador.start_recording()
                input("Presiona ENTER para finalizar la demostración...")
                recorded_steps = grabador.stop_recording()
                if recorded_steps:
                    self.memoria.save_demonstration(initial_user_message, recorded_steps)
                task_completed = True
                self.state = AgentState.TASK_COMPLETED
            elif accion_ejecutada in ["responder_chat", "finalizar_tarea", "tarea_completada"]:
                task_completed = True
                self.state = AgentState.TASK_COMPLETED
            else:
                self.state = AgentState.PLANNING

        if not task_completed:
            self.state = AgentState.TASK_FAILED
        
        self.state = AgentState.IDLE

if __name__ == '__main__':
    print("Este es el nuevo agente. No contiene un bloque de prueba principal.")