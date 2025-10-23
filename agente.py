import time
import json
import logging
import threading
import pyautogui

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
from model_manager import ModelProvider

# Lock global para serializar las llamadas al modelo de IA
model_api_lock = threading.Lock()

class Agente:
    def __init__(self, model_provider: ModelProvider, model_name: str, id_ventana=None, id_objetivo=None, callback_hablar=None, callback_finalizar=None, callback_log=None):
        self.comunicador = Comunicador(callback_hablar, callback_finalizar, callback_log)
        setup_logging(comunicador=self.comunicador)
        self.logger = logging.getLogger("InteractIA")
        self.logger.info(f"Inicializando el agente InteractIA (ID: {id_ventana})...")
        
        self.model_provider = model_provider
        if not self.model_provider:
            self.logger.critical("¡ERROR CRÍTICO! El agente se inicializó sin un proveedor de modelo de IA.")
            self.operativo = False
            return
        
        # Configurar el modelo específico en el proveedor
        try:
            self.model_provider.set_model(model_name)
            self.logger.info(f"Modelo '{model_name}' establecido en el proveedor.")
        except Exception as e:
            self.logger.critical(f"¡ERROR CRÍTICO! No se pudo establecer el modelo '{model_name}' en el proveedor: {e}")
            self.operativo = False
            return

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
            self.logger.error("El agente no puede operar debido a una configuración base faltante.")
            return

        self.operativo = True
        self.controlador = Controlador()
        self.vision = Vision()
        self.kb = KnowledgeBase()
        self.memoria = MongoDBChatMemory(model_provider=self.model_provider)
        
        self.objetivo = None
        self.historial_acciones = []
        
        historial_complejo = self.memoria._recuperar_historial_crudo(session_key=self.mi_id_ventana) if self.memoria.operativo else []
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

    # ... (El resto de la clase no cambia)
    def _call_model(self, prompt: str, image=None) -> dict:
        self.logger.info("Esperando el bloqueo de la API del modelo...")
        with model_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                decision = self.model_provider.generate_content(prompt, image)
                self.logger.debug(f"Respuesta del modelo: {decision}")
                return decision
            except Exception as e:
                self.logger.error(f"ERROR al llamar al proveedor del modelo de IA: {e}", exc_info=True)
                return {"accion": None, "razon": f"Error en la llamada a la API a través del proveedor: {e}"}

    def establecer_objetivo(self, objetivo):
        self.logger.info(f"Llamada a establecer_objetivo con: '{objetivo}'")
        if self.estado_agente.get('esperando_aprobacion'):
            self._manejar_respuesta_aprendizaje(objetivo)
            return
        if objetivo.strip().lower() == '/aprender_de_historial':
            threading.Thread(target=self.iniciar_ciclo_meta_aprendizaje).start()
            return
        self.objetivo = objetivo
        self.historial_acciones = []
        self.resultado_accion_anterior = None
        rol = 'usuario'
        contenido = {'texto': objetivo, 'adjunto': None}
        self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
        self.historial_conversacion.append({'rol': rol, 'contenido': objetivo})
        self.logger.info(f"Objetivo establecido: {self.objetivo}")

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
        habilidades_contextuales = self.kb.conocer_habilidades_por_contexto([contexto_actual, "General"])
        prompt = self._construir_prompt(
            resumen_memoria=resumen_memoria, 
            habilidades_disponibles=habilidades_contextuales,
            feedback_anterior=self.resultado_accion_anterior
        )
        return self._call_model(prompt, estado_observado['captura'])

    def _construir_prompt(self, resumen_memoria: str, habilidades_disponibles: list = None, feedback_anterior=None):
        contexto_habilidad = ""
        if habilidades_disponibles:
            info_habilidades = []
            for hab in habilidades_disponibles:
                datos_habilidad = hab.get("datos", {})
                acciones_habilidad = datos_habilidad.get("acciones", [])
                if not acciones_habilidad: continue
                acciones_para_llm = [{k: v for k, v in accion_def.items() if k != 'secuencia_primitivas'} for accion_def in acciones_habilidad]
                info_relevante = {
                    "nombre_habilidad": hab.get("nombre_recurso"),
                    "descripcion": datos_habilidad.get("descripcion"),
                    "acciones_disponibles": acciones_para_llm
                }
                info_habilidades.append(json.dumps(info_relevante, indent=2, ensure_ascii=False))
            if info_habilidades:
                contexto_habilidad = "HABILIDADES DISPONIBLES (Herramientas y Conocimiento):\n" + "\n---\n".join(info_habilidades)
            else:
                contexto_habilidad = "No se encontró conocimiento aplicable."
        else:
            contexto_habilidad = "No se encontró conocimiento aplicable."
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
Si el objetivo actual puede ser satisfecho completamente con una respuesta verbal o si el usuario te pide explícitamente que "hables" o "respondas hablando", debes priorizar la acción "hablar". Si la tarea ha sido completada y solo necesitas informar, usa la acción "finalizar".

RESPUESTA (ÚNICAMENTE JSON con la siguiente estructura obligatoria):
{{
  "pensamiento": "<Tu razonamiento para elegir esta acción. Describe tu plan paso a paso.>",
  "accion": "<nombre_de_la_accion_o_habilidad>",
  "params": {{ "<nombre_param>": "<valor_param>" }}
}}
Ejemplos de acciones de comunicación:
- Para responder verbalmente: {{"accion": "hablar", "params": {{"mensaje": "Aquí está la información solicitada."}}}}
- Para finalizar una tarea con un mensaje: {{"accion": "finalizar", "params": {{"razon": "La tarea de buscar información ha sido completada."}}}}
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
        habilidad_doc = self.kb.conocer_habilidad_por_accion(accion_actual)
        if not habilidad_doc:
            return {'exito': False, 'razon': f"No se encontró la habilidad '{accion_actual}' en la KB."}
        accion_definicion = next((a for a in habilidad_doc.get("datos", {}).get("acciones", []) if a.get("nombre") == accion_actual), None)
        if not accion_definicion or "secuencia_primitivas" not in accion_definicion:
            return {'exito': False, 'razon': f"No se encontró una 'secuencia_primitivas' para la acción '{accion_actual}'."}
        secuencia = accion_definicion["secuencia_primitivas"]
        for i, paso in enumerate(secuencia):
            accion_paso = paso.get("accion")
            params_paso_plantilla = paso.get("params", {})
            params_paso_reales = {}
            try:
                for key, value in params_paso_plantilla.items():
                    params_paso_reales[key] = value.format(**params_actuales) if isinstance(value, str) else value
            except KeyError as e:
                return {'exito': False, 'razon': f"Faltó el parámetro de entrada: {e}"}
            if accion_paso in self.habilidades_fundamentales:
                resultado_paso = self._ejecutar_accion_primitiva(accion_paso, params_paso_reales)
            else:
                resultado_paso = self._ejecutar_habilidad({"accion": accion_paso, "params": params_paso_reales})
            if not resultado_paso['exito']:
                return {'exito': False, 'razon': f"La habilidad '{accion_actual}' falló en el paso {i+1} ('{accion_paso}'). Razón: {resultado_paso['razon']}"}
        return {'exito': True, 'razon': f"Habilidad '{accion_actual}' completada."}

    def stream_run(self):
        if not self.operativo or not self.objetivo:
            self.logger.error("Agente no operativo o sin objetivo.")
            return
        self.logger.info(f"--- INICIANDO BUCLE DE EJECUCIÓN para: '{self.objetivo}' ---")
        max_intentos = 5
        intentos = 0
        while intentos < max_intentos:
            intentos += 1
            self.logger.info(f"--- Ciclo de Ejecución: Intento {intentos}/{max_intentos} ---")
            estado_observado = self.observar()
            decision = self.pensar(estado_observado)
            self.logger.info(f"Decisión del modelo: {decision.get('accion')}, Params: {decision.get('params')}")
            accion = decision.get("accion")
            pensamiento = decision.get("pensamiento", "").lower()

            # --- Nuevo: Forzar finalizar si el pensamiento indica tarea completada ---
            if ("tarea completada" in pensamiento or "objetivo alcanzado" in pensamiento) and accion != "finalizar":
                self.logger.info("Pensamiento indica tarea completada, forzando acción 'finalizar'.")
                decision["accion"] = "finalizar"
                decision["params"] = {"razon": "Tarea completada según el pensamiento del agente."}
                accion = "finalizar"
            # --- Fin Nuevo ---

            if not accion:
                self.resultado_accion_anterior = {'exito': False, 'razon': decision.get('razon', 'El modelo no devolvió una acción.')}
                self.logger.error(self.resultado_accion_anterior['razon'])
                time.sleep(1)
                continue
            lock_manager.acquire_lock(self.mi_id_ventana)
            try:
                if accion in self.habilidades_fundamentales:
                    if accion in ["pedir_aclaracion", "hablar", "proponer_aprendizaje", "finalizar"]:
                        self._ejecutar_accion_comunicacion(decision)
                        if accion == "finalizar": break
                    else:
                        self.resultado_accion_anterior = self._ejecutar_accion_primitiva(accion, decision.get("params", {}))
                else:
                    self.resultado_accion_anterior = self._ejecutar_habilidad(decision)
            finally:
                lock_manager.release_lock(self.mi_id_ventana)
            if not self.resultado_accion_anterior['exito']:
                self.logger.error(f"La acción '{accion}' ha fallado. Razón: {self.resultado_accion_anterior['razon']}. El agente re-evaluará.")
            time.sleep(1)
        if intentos >= max_intentos:
            self.logger.error("Se alcanzó el número máximo de intentos.")
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
            mensaje = f"He identificado una posible nueva habilidad: '{nombre_habilidad}' ({descripcion}). ¿Quieres que la guarde?"
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
        self.logger.info("--- Fase: Reflexionar sobre el Éxito ---")
        acciones_realizadas_str = json.dumps(self.historial_acciones, indent=2)
        prompt_reflexion = f'''TAREA: Analiza esta secuencia de acciones exitosa. ¿Representa una habilidad útil y generalizable?'''
        decision_aprendizaje = self._call_model(prompt_reflexion, None)
        if decision_aprendizaje and decision_aprendizaje.get("aprender"):
            self._ejecutar_accion_comunicacion({"accion": "proponer_aprendizaje", "params": decision_aprendizaje})

    def _manejar_respuesta_aprendizaje(self, respuesta_usuario: str):
        propuesta = self.estado_agente.get('propuesta_aprendizaje')
        if not propuesta: return
        if 'si' in respuesta_usuario.lower():
            nombre_recurso = f"habilidad_{propuesta.get('nombre_habilidad')}"
            # ... (código para guardar habilidad)
            self.kb.aprender_habilidad(nombre_recurso, "Habilidad Compleja Autónoma", datos_habilidad)
            self.comunicador.hablar(f"¡Genial! He guardado la nueva habilidad.")
        else:
            self.comunicador.hablar("Entendido. Descartaré la propuesta.")
        self.estado_agente['esperando_aprobacion'] = False
        self.estado_agente['propuesta_aprendizaje'] = None

    def _publicar_estado(self, decision: dict, estado_bucle: str): pass
    def iniciar_ciclo_meta_aprendizaje(self): pass