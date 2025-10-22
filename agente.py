import time
import json
import re
import google.generativeai as genai
from PIL import Image
import pyautogui
import logging
import threading
import importlib
import inspect

# Módulos de la aplicación
import config
from controlador import Controlador
from vision import Vision
from knowledge_base import KnowledgeBase
from memoria_chat_mongodb import MongoDBChatMemory
from logger_config import setup_logging
from comunicador import Comunicador
from contexto_manager import detectar_contexto_actual
import lock_manager

# Lock global para serializar las llamadas a la API de Gemini y evitar cruces
gemini_api_lock = threading.Lock()

class Agente:
    def __init__(self, id_ventana=None, id_objetivo=None, callback_hablar=None, callback_finalizar=None, callback_log=None):
        self.comunicador = Comunicador(callback_hablar, callback_finalizar, callback_log)
        setup_logging(comunicador=self.comunicador)
        self.logger = logging.getLogger("InteractIA")
        self.logger.info(f"Inicializando el agente InteractIA (ID: {id_ventana})...")
        
        self.mi_id_ventana = id_ventana
        self.modo = 'autonomo'
        self.titulo_objetivo = None
        self.resultado_accion_anterior = None

        if id_objetivo:
            self.modo = 'controlador'
            self.titulo_objetivo = f"interactia-{id_objetivo}"
            self.logger.info(f"Agente en modo 'controlador'. Objetivo: {self.titulo_objetivo}")

        if not config.verificar_configuracion():
            self.operativo = False
            self.logger.error("El agente no puede operar debido a una configuración faltante.")
            return

        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.modelo = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
            self.logger.info("Modelo de IA configurado exitosamente.")
            self.operativo = True
        except Exception as e:
            self.logger.error(f"ERROR al configurar el modelo de IA: {e}")
            self.operativo = False
            return

        self.controlador = Controlador()
        self.vision = Vision()
        self.kb = KnowledgeBase()
        self.memoria = MongoDBChatMemory(modelo=self.modelo)
        
        self.objetivo = None
        self.historial_acciones = []
        
        historial_complejo = self.memoria._recuperar_historial_crudo(
            session_key=self.mi_id_ventana
        ) if self.memoria.operativo else []
        self.historial_conversacion = self.memoria.convertir_historial_a_formato_simple(historial_complejo)
        
        self.estado_agente = {}

        habilidades_fundamentales_doc = self.kb.conocer_habilidad('habilidades_fundamentales_agente')
        if not habilidades_fundamentales_doc:
            self.logger.critical("¡ERROR CRÍTICO! No se pudieron cargar las habilidades fundamentales.")
            self.operativo = False
            self.habilidades_fundamentales = []
        else:
            self.logger.info("Habilidades fundamentales cargadas correctamente.")
            self.habilidades_fundamentales = [accion['nombre'] for accion in habilidades_fundamentales_doc['datos']['acciones']]


    def establecer_objetivo(self, objetivo):
        self.logger.info(f"Llamada a establecer_objetivo con: '{objetivo}'")
        self.logger.info(f"Estado de 'esperando_aprobacion' antes del chequeo: {self.estado_agente.get('esperando_aprobacion')}")

        if self.estado_agente.get('esperando_aprobacion'):
            self.logger.info("Agente está esperando aprobación. La entrada se tratará como una respuesta a la propuesta de aprendizaje.")
            self._manejar_respuesta_aprendizaje(objetivo)
            return

        if objetivo.strip().lower() == '/aprender_de_historial':
            self.logger.info("Comando de meta-aprendizaje recibido.")
            threading.Thread(target=self.iniciar_ciclo_meta_aprendizaje).start()
            return

        self.objetivo = objetivo
        self.logger.info(f"self.objetivo ha sido establecido a: '{self.objetivo}'")

        self.historial_acciones = []
        self.resultado_accion_anterior = None

        rol = 'usuario'
        contenido = {'texto': objetivo, 'adjunto': None}
        self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
        self.historial_conversacion.append({'rol': rol, 'contenido': objetivo})
        self.logger.info(f"Objetivo establecido y guardado en la memoria: {self.objetivo}")

    def observar(self):
        self.logger.info("--- Fase: Observar ---")
        captura = self.vision.capturar_entorno(id_ventana_propia=self.mi_id_ventana)
        texto = self.vision.leer_texto_en_pantalla(captura)
        return {'captura': captura, 'texto': texto}

    def pensar(self, estado_observado: dict):
        self.logger.info("--- Fase: Pensar ---")
        if not self.objetivo:
            return {"accion": "finalizar", "params": {"razon": "No hay objetivo"}}

        resumen_memoria = self.memoria.resumir_y_consultar(session_key=self.mi_id_ventana)
        
        contexto_actual = detectar_contexto_actual()
        self.logger.info(f"Contexto de aplicación detectado: {contexto_actual}")
        habilidades_contextuales = self.kb.conocer_habilidades_por_contexto([contexto_actual, "General"])
        self.logger.info(f"Cargadas {len(habilidades_contextuales)} habilidades para los contextos '{contexto_actual}' y 'General'.")

        prompt = self._construir_prompt(
            resumen_memoria=resumen_memoria, 
            habilidades_disponibles=habilidades_contextuales,
            feedback_anterior=self.resultado_accion_anterior
        )
        
        self.logger.debug(f"--- PROMPT PARA EL MODELO ---\n{prompt}")
        return self.llm_call(prompt, estado_observado['captura'])

    def _construir_prompt(self, resumen_memoria: str, habilidades_disponibles: list = None, feedback_anterior=None):
        
        contexto_habilidad = ""
        if habilidades_disponibles:
            info_habilidades = []
            for hab in habilidades_disponibles:
                datos_habilidad = hab.get("datos", {})
                acciones_habilidad = datos_habilidad.get("acciones", [])
                
                if not acciones_habilidad: # Omitir habilidades sin acciones definidas
                    continue

                acciones_para_llm = []
                for accion_def in acciones_habilidad:
                    # Mantener todas las claves excepto 'secuencia_primitivas', que es un detalle de implementación interno.
                    # Esto asegura que 'params' siempre se incluya para que el LLM sepa qué proporcionar.
                    action_info = {k: v for k, v in accion_def.items() if k != 'secuencia_primitivas'}
                    acciones_para_llm.append(action_info)

                info_relevante = {
                    "nombre_habilidad": hab.get("nombre_recurso"),
                    "descripcion": datos_habilidad.get("descripcion"),
                    "acciones_disponibles": acciones_para_llm
                }
                info_habilidades.append(json.dumps(info_relevante, indent=2, ensure_ascii=False))
            
            if info_habilidades:
                contexto_habilidad = "HABILIDADES DISPONIBLES (Herramientas y Conocimiento):\n" + "\n---\n".join(info_habilidades)
            else:
                contexto_habilidad = "No se encontró conocimiento aplicable en la base de datos para este contexto."
        else:
            contexto_habilidad = "No se encontró conocimiento aplicable en la base de datos para este contexto."

        contexto_feedback = ""
        if feedback_anterior:
            estado = "ÉXITO" if feedback_anterior['exito'] else "FALLO"
            contexto_feedback = f"RESULTADO DE LA ACCIÓN ANTERIOR: {estado}. Razón: {feedback_anterior['razon']}.\n"
            if not feedback_anterior['exito']:
                contexto_feedback += "Debes re-evaluar y probar un enfoque diferente."

        prompt = f'''
Tu rol es InteractIA, un agente de IA que completa tareas controlando un ordenador.
Tu proceso se basa en un ciclo de **Observar, Pensar, Actuar**.

OBJETIVO ACTUAL: '{self.objetivo}'

{contexto_feedback}

CONTEXTO DE MEMORIA RELEVANTE:
{resumen_memoria}

{contexto_habilidad}

TAREA PRINCIPAL:
Tu deber es analizar la pantalla, el objetivo y el feedback para decidir la siguiente acción.
1.  **Verifica si el Objetivo está Cumplido**: Si después de observar, determinas que el objetivo ya se ha conseguido, tu ÚNICA acción debe ser `finalizar`.
2.  **Analiza y Planifica**: Si el objetivo no está cumplido, observa la pantalla y el contexto. Si tu acción anterior falló, crea un plan alternativo.
3.  **Decide la Próxima Acción**: Elige la siguiente acción o habilidad de alto nivel para avanzar en tu plan. No inventes acciones, usa solo las de la lista.
4.  **Define los Parámetros**: Especifica los parámetros exactos que la acción necesita.

RESPUESTA (ÚNICAMENTE JSON con la siguiente estructura obligatoria):
{{
  "pensamiento": "<Tu razonamiento para elegir esta acción. Describe tu plan paso a paso.>",
  "accion": "<nombre_de_la_accion_o_habilidad>",
  "params": {{ "<nombre_param>": "<valor_param>" }}
}}
'''
        return prompt

    def _ejecutar_accion_primitiva(self, accion: str, params: dict):
        self.logger.info(f"--- Ejecutando Acción Primitiva: {accion} ---")
        try:
            if accion == "clic":
                ancho, alto = pyautogui.size()
                x_abs = int(params.get('x_rel', 0.5) * ancho)
                y_abs = int(params.get('y_rel', 0.5) * alto)
                self.controlador.clic(x_abs, y_abs)
            elif accion == "escribir":
                self.controlador.escribir(params.get('texto', ''))
            elif accion == "presionar_tecla":
                self.controlador.presionar_tecla(params.get('tecla', ''))
            elif accion == "scroll":
                self.controlador.scroll(params.get('direccion'), params.get('clics'))
            elif accion == "arrastrar_barra":
                self.controlador.arrastrar_barra(params.get('direccion'), params.get('porcentaje'))
            elif accion == "cambiar_ventana":
                self.controlador.mantener_tecla('alt')
                for _ in range(params.get('tabs', 1)):
                    self.controlador.presionar_tecla('tab')
                    self.controlador.esperar(0.2)
                self.controlador.soltar_tecla('alt')
            elif accion == "esperar":
                self.controlador.esperar(params.get('segundos', 1))
            else:
                self.logger.warning(f"Acción primitiva '{accion}' desconocida.")
                return {'exito': False, 'razon': f"Acción primitiva '{accion}' no reconocida."}
            return {'exito': True, 'razon': f"Acción '{accion}' ejecutada."}
        except Exception as e:
            self.logger.error(f"ERROR al ejecutar la acción primitiva '{accion}': {e}", exc_info=True)
            return {'exito': False, 'razon': f"Excepción al ejecutar '{accion}': {e}"}

    def _ejecutar_habilidad(self, decision: dict):
        accion_actual = decision.get("accion")
        params_actuales = decision.get("params", {})
        self.logger.info(f"--- Ejecutando Habilidad Compleja: {accion_actual} con params {params_actuales} ---")

        # 1. Buscar la habilidad en la KB
        habilidad_doc = self.kb.conocer_habilidad_por_accion(accion_actual)
        if not habilidad_doc:
            msg = f"No se encontró la habilidad '{accion_actual}' en la KB."
            self.logger.error(msg)
            return {'exito': False, 'razon': msg}

        # 2. Encontrar la definición de la acción específica dentro de la habilidad
        accion_definicion = next((a for a in habilidad_doc.get("datos", {}).get("acciones", []) if a.get("nombre") == accion_actual), None)

        if not accion_definicion or "secuencia_primitivas" not in accion_definicion:
            msg = f"No se encontró una 'secuencia_primitivas' para la acción '{accion_actual}' en la KB."
            self.logger.error(msg)
            return {'exito': False, 'razon': msg}

        # 3. Ejecutar la secuencia de acciones
        secuencia = accion_definicion["secuencia_primitivas"]
        self.logger.info(f"Ejecutando secuencia de {len(secuencia)} pasos para '{accion_actual}'.")

        for i, paso in enumerate(secuencia):
            accion_paso = paso.get("accion")
            params_paso_plantilla = paso.get("params", {})
            
            # Reemplazar placeholders en los parámetros de la plantilla con los parámetros de la decisión actual
            params_paso_reales = {}
            for key, value in params_paso_plantilla.items():
                if isinstance(value, str):
                    try:
                        params_paso_reales[key] = value.format(**params_actuales)
                    except KeyError as e:
                        msg = f"La habilidad '{accion_actual}' no pudo formatear el parámetro '{key}' para el paso '{accion_paso}'. Faltó el parámetro de entrada: {e}"
                        self.logger.error(msg)
                        return {'exito': False, 'razon': msg}
                else:
                    params_paso_reales[key] = value

            self.logger.info(f"Paso {i+1}/{len(secuencia)}: Ejecutando '{accion_paso}' con params {params_paso_reales}")
            
            # Determinar si el paso es una acción primitiva o una habilidad compleja
            if accion_paso in self.habilidades_fundamentales:
                # Es una acción primitiva
                resultado_paso = self._ejecutar_accion_primitiva(accion_paso, params_paso_reales)
            else:
                # Es una habilidad compleja, llamarla recursivamente
                self.logger.info(f"'{accion_paso}' es una habilidad compleja. Llamada recursiva.")
                decision_paso = {"accion": accion_paso, "params": params_paso_reales}
                resultado_paso = self._ejecutar_habilidad(decision_paso)

            if not resultado_paso['exito']:
                msg = f"La habilidad '{accion_actual}' falló en el paso {i+1} ('{accion_paso}'). Razón: {resultado_paso['razon']}"
                self.logger.error(msg)
                return {'exito': False, 'razon': msg}

        msg = f"Habilidad '{accion_actual}' completada exitosamente tras {len(secuencia)} pasos."
        self.logger.info(msg)
        return {'exito': True, 'razon': msg}


    def stream_run(self):
        if not self.operativo or not self.objetivo:
            if not self.operativo:
                self.comunicador.hablar("Error: Agente no operativo. Por favor, revisa la configuración y los logs para más detalles.")
                self.logger.error("Agente no operativo. Verifique la configuración de API y DB, y la carga de habilidades fundamentales.")
            elif not self.objetivo:
                self.comunicador.hablar("Error: No se ha establecido un objetivo para el agente.")
                self.logger.error("No se ha establecido un objetivo para el agente.")
            return

        self.logger.info(f"--- INICIANDO BUCLE DE EJECUCIÓN para: '{self.objetivo}' ---")
        
        max_intentos = 5
        intentos = 0
        while intentos < max_intentos:
            intentos += 1
            self.logger.info(f"--- Ciclo de Ejecución: Intento {intentos}/{max_intentos} ---")

            # 1. OBSERVAR
            estado_observado = self.observar()
            
            # 2. PENSAR
            decision = self.pensar(estado_observado)
            self._publicar_estado(decision, "PENSANDO")
            self.logger.info(f"Decisión del modelo: {decision.get('accion')}, Params: {decision.get('params')}")


            # 3. ACTUAR
            accion = decision.get("accion")
            if not accion:
                self.resultado_accion_anterior = {'exito': False, 'razon': decision.get('razon', 'El modelo no devolvió una acción.')}
                self.logger.error(self.resultado_accion_anterior['razon'])
                time.sleep(1)
                continue

            lock_manager.acquire_lock(self.mi_id_ventana)
            try:
                if accion in self.habilidades_fundamentales:
                    # Es una acción primitiva de comunicación o de UI
                    if accion in ["pedir_aclaracion", "hablar", "proponer_aprendizaje", "finalizar"]:
                        self._ejecutar_accion_comunicacion(decision)
                        if accion == "finalizar": break
                    else:
                        # Es una acción primitiva de UI
                        self.resultado_accion_anterior = self._ejecutar_accion_primitiva(accion, decision.get("params", {}))
                else:
                    # Es una habilidad compleja que debe ser ejecutada
                    self.resultado_accion_anterior = self._ejecutar_habilidad(decision)
            finally:
                lock_manager.release_lock(self.mi_id_ventana)

            self._publicar_estado(decision, f"ACTUADO: {'ÉXITO' if self.resultado_accion_anterior['exito'] else 'FALLO'}")
            
            if self.resultado_accion_anterior['exito']:
                self.logger.info(f"La acción '{accion}' tuvo éxito. Razón: {self.resultado_accion_anterior['razon']}")
            else:
                self.logger.error(f"La acción '{accion}' ha fallado. Razón: {self.resultado_accion_anterior['razon']}. El agente re-evaluará.")

            time.sleep(1)
        
        if intentos >= max_intentos:
            self.logger.error("Se alcanzó el número máximo de intentos. Finalizando el bucle.")

        self.logger.info("--- BUCLE DE EJECUCIÓN FINALIZADO ---")
        self.comunicador.finalizar_habla()


    def _ejecutar_accion_comunicacion(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        mensaje = ""
        if accion in ["pedir_aclaracion", "hablar"]:
            mensaje = params.get('pregunta', params.get('mensaje', 'No sé qué decir.'))
            self.comunicador.hablar(mensaje)

        elif accion == "proponer_aprendizaje":
            nombre_habilidad = params.get('nombre_habilidad', 'habilidad_desconocida')
            descripcion = params.get('descripcion', 'Sin descripción.')
            self.estado_agente['esperando_aprobacion'] = True
            self.estado_agente['propuesta_aprendizaje'] = params
            mensaje = f"He identificado una posible nueva habilidad: '{nombre_habilidad}' ({descripcion}). ¿Quieres que la guarde en mi base de conocimiento? (responde 'si' o 'no')"
            self.comunicador.hablar(mensaje)

        elif accion == "finalizar":
            mensaje = params.get('razon', 'He completado la tarea.')
            self.comunicador.hablar(f"Finalizando: {mensaje}")

        if mensaje:
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})
        
        self.resultado_accion_anterior = {'exito': True, 'razon': f"Acción de comunicación '{accion}' ejecutada."}

    def _reflexionar_y_aprender(self):
        """
        Analiza el historial de acciones de una tarea completada y propone aprender una nueva habilidad.
        """
        self.logger.info("--- Fase: Reflexionar sobre el Éxito ---")
        
        # Construir un prompt para que el LLM analice la secuencia de acciones
        acciones_realizadas_str = json.dumps(self.historial_acciones, indent=2)
        prompt_reflexion = f"""
        He completado con éxito el objetivo '{self.objetivo}'.
        Para ello, he ejecutado la siguiente secuencia de acciones:
        {acciones_realizadas_str}

        TAREA: Analiza esta secuencia. ¿Representa una habilidad útil y generalizable?
        - Si NO es una habilidad útil (ej. demasiado simple, muy específica, o un error), responde solo con: {{'aprender': false}}
        - Si SÍ es una habilidad útil, responde con un JSON que la describa. Identifica las partes variables y conviértelas en parámetros.

        Ejemplo de respuesta afirmativa:
        {{
          "aprender": true,
          "nombre_habilidad": "buscar_archivo_en_explorador",
          "descripcion": "Abre el explorador y busca un archivo por su nombre.",
          "parametros_identificados": ["nombre_archivo"],
          "secuencia_primitivas": [
            {{"accion": "presionar_tecla", "params": {{"tecla": "win+e"}}}},
            {{"accion": "escribir", "params": {{"texto": "{{nombre_archivo}}"}}}},
            {{"accion": "presionar_tecla", "params": {{"tecla": "enter"}}}}
          ]
        }}

        RESPUESTA (solo JSON):
        """
        
        # Llamada al LLM (sin imagen, solo texto)
        # Nota: llm_call necesitará una pequeña adaptación para llamadas de solo texto.
        # Por ahora, asumimos que puede manejarlo o creamos una función wrapper.
        decision_aprendizaje = self.llm_call(prompt_reflexion, None) # Pasamos None para la imagen

        if decision_aprendizaje and decision_aprendizaje.get("aprender"):
            self.logger.info(f"Reflexión sugiere aprender la habilidad: {decision_aprendizaje.get('nombre_habilidad')}")
            self._ejecutar_accion_comunicacion({"accion": "proponer_aprendizaje", "params": decision_aprendizaje})


    def llm_call(self, prompt: str, captura_entorno: Image.Image):
        self.logger.info("Esperando el bloqueo de la API de Gemini...")
        with gemini_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                contenido = [prompt]
                if captura_entorno:
                    contenido.append(captura_entorno)
                
                respuesta = self.modelo.generate_content(contenido)
                self.logger.debug(f"Respuesta cruda del modelo: {respuesta.text}")

                # Extraer el bloque JSON usando una expresión regular más robusta
                match = re.search(r'\{.*\}', respuesta.text, re.DOTALL)
                if match:
                    json_text = match.group(0)
                else:
                    raise json.JSONDecodeError("No se encontró un objeto JSON en la respuesta.", respuesta.text, 0)

                decision = json.loads(json_text)
                return decision
            except json.JSONDecodeError as e:
                error_msg = f"Error de parseo en la respuesta del modelo. Respuesta cruda: '{respuesta.text}'"
                self.logger.error(f"ERROR al parsear JSON: {e}. {error_msg}")
                return {"accion": None, "razon": f"JSONDecodeError: {error_msg}"}
            except Exception as e:
                self.logger.error(f"ERROR al llamar al modelo de IA: {e}", exc_info=True)
                return {"accion": None, "razon": f"Error en el módulo de decisión al llamar a la API: {e}"}

    def _manejar_respuesta_aprendizaje(self, respuesta_usuario: str):
        """Gestiona la respuesta 'si' o 'no' del usuario a una propuesta de aprendizaje."""
        propuesta = self.estado_agente.get('propuesta_aprendizaje')
        if not propuesta:
            return

        if 'si' in respuesta_usuario.lower():
            nombre_recurso = f"habilidad_{propuesta.get('nombre_habilidad')}"
            datos_habilidad = {
                "descripcion": f"Habilidad aprendida autónomamente para: {propuesta.get('descripcion')}",
                "contexto_aplicacion": ["General"], # Se puede mejorar para detectar contexto
                "acciones": [
                    {
                        "nombre": propuesta.get('nombre_habilidad'),
                        "descripcion": propuesta.get('descripcion'),
                        "params": [{"nombre": p} for p in propuesta.get("parametros_identificados", [])],
                        "secuencia_primitivas": propuesta.get('secuencia_primitivas')
                    }
                ]
            }
            self.kb.aprender_habilidad(nombre_recurso, "Habilidad Compleja Autónoma", datos_habilidad)
            self.comunicador.hablar(f"¡Genial! He guardado la nueva habilidad '{propuesta.get('nombre_habilidad')}' en mi memoria.")
        else:
            self.comunicador.hablar("Entendido. Descartaré la propuesta.")

        # Limpiar el estado
        self.estado_agente['esperando_aprobacion'] = False
        self.estado_agente['propuesta_aprendizaje'] = None

    def _publicar_estado(self, decision: dict, estado_bucle: str): pass
    def iniciar_ciclo_meta_aprendizaje(self): pass

if __name__ == '__main__':
    def main_test():
        import subprocess
        setup_logging(log_level=logging.INFO)
        agente = Agente(id_ventana="test_agent_main")
        if agente.operativo:
            # El objetivo ahora es que el agente abra notepad y escriba en él.
            agente.establecer_objetivo("Abre el bloc de notas y escribe 'Hola Mundo. Esto es una prueba.'")
            agente.stream_run()
            
            # Opcional: cerrar notepad al final para limpiar
            try:
                # Este comando puede variar en función del sistema operativo y el idioma
                subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], check=False)
                print("Intento de cierre de Notepad finalizado.")
            except Exception as e:
                print(f"No se pudo cerrar Notepad automáticamente: {e}")

    main_test()