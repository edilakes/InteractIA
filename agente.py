import time
import json
import logging
import threading
import pyautogui
import re

# Módulos de la aplicación
import config
from controlador import Controlador
from vision import Vision
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
        self.parada_emergencia = threading.Event()
        self.esperando_respuesta_usuario = False

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
        self.memoria = MongoDBChatMemory(model_provider=self.model_provider)
        
        self.objetivo = None
        self.historial_acciones = []
        
        historial_complejo = self.memoria._recuperar_historial_crudo(session_key=self.mi_id_ventana) if self.memoria.operativo else []
        self.historial_conversacion = self.memoria.convertir_historial_a_formato_simple(historial_complejo)
        
        self.estado_agente = {}

        self.logger.info("KnowledgeBase ha sido eliminada. Habilidades fundamentales no cargadas.")
        self.habilidades = {} # No longer using pre-defined skills in this manner


    def detener_proceso_emergencia(self):
        self.parada_emergencia.set()
        self.logger.warning("¡PARADA DE EMERGENCIA ACTIVADA!")

    def _limpiar_y_parsear_json(self, texto_respuesta: str) -> dict:
        """
        Limpia y parsea una cadena que se espera contenga JSON.
        - Extrae el contenido de bloques de código markdown (```json ... ```).
        - Intenta parsear el JSON.
        - Devuelve un diccionario de acción nula si el parseo falla.
        """
        self.logger.debug(f"Limpiando texto para JSON: '{texto_respuesta}'")
        
        # Buscar el bloque de código JSON
        match = re.search(r'```json\s*(\{.*?\})\s*```', texto_respuesta, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Si no hay bloque de código, buscar el primer '{' y el último '}'
            start = texto_respuesta.find('{')
            end = texto_respuesta.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = texto_respuesta[start:end+1]
            else:
                json_str = texto_respuesta

        self.logger.debug(f"Cadena JSON extraída: '{json_str}'")
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar JSON: {e}. Contenido: '{json_str}'")
            return {"accion": None, "razon": f"Error de decodificación JSON en la respuesta: {e}", "respuesta_original": json_str}

    def _call_model(self, prompt: str, image=None) -> dict:
        self.logger.info("Esperando el bloqueo de la API del modelo...")
        with model_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                respuesta_bruta = self.model_provider.generate_content(prompt, image)
                self.logger.debug(f"Respuesta BRUTA del modelo: {respuesta_bruta}")

                texto_para_parsear = None
                if isinstance(respuesta_bruta, dict):
                    # Caso común: {'text': '...'} o similar
                    if 'text' in respuesta_bruta and isinstance(respuesta_bruta['text'], str):
                        texto_para_parsear = respuesta_bruta['text']
                    else:
                        # Si es un dict pero no tiene 'text', lo intentamos convertir a string
                        texto_para_parsear = str(respuesta_bruta)
                elif isinstance(respuesta_bruta, str):
                    texto_para_parsear = respuesta_bruta
                
                if not texto_para_parsear:
                    self.logger.error("La respuesta del modelo está vacía o en un formato inesperado.")
                    return {"accion": None, "razon": "Respuesta vacía o inesperada del modelo.", "respuesta_original": str(respuesta_bruta)}

                decision = self._limpiar_y_parsear_json(texto_para_parsear)
                
                if not decision.get("accion"):
                     self.logger.warning(f"El JSON parseado no contiene una acción o falló el parseo. Respuesta original: {texto_para_parsear}")
                     # Si el parseo falló, la razón ya está en 'decision'
                     if "respuesta_original" not in decision:
                         decision["respuesta_original"] = texto_para_parsear

                return decision

            except Exception as e:
                self.logger.error(f"ERROR al llamar al proveedor del modelo de IA: {e}", exc_info=True)
                return {"accion": None, "razon": f"Error en la llamada a la API a través del proveedor: {e}"}

    def _set_initial_objective(self, objetivo):
        self.logger.info(f"Estableciendo objetivo inicial desde el historial: '{objetivo}'")
        self.objetivo = objetivo
        self.historial_acciones = []
        self.resultado_accion_anterior = None
        self.parada_emergencia.clear()
        # No guardar en memoria, ya está ahí

    def establecer_objetivo(self, objetivo):
        self.logger.info(f"Llamada a establecer_objetivo con: '{objetivo}'")
        self.esperando_respuesta_usuario = False
        if self.estado_agente.get('esperando_aprobacion'):
            self._manejar_respuesta_aprendizaje(objetivo)
            return

        self.objetivo = objetivo
        self.historial_acciones = []
        self.resultado_accion_anterior = None
        self.parada_emergencia.clear()
        rol = 'usuario'
        contenido = {'texto': objetivo, 'adjunto': None}
        self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
        self.historial_conversacion.append({'rol': rol, 'contenido': objetivo})
        self.logger.info(f"Objetivo establecido: {self.objetivo}")

    def observar(self):
        self.logger.debug("--- Fase: Observar (Inicio) ---")
        captura = self.vision.capturar_entorno(id_ventana_propia=self.mi_id_ventana)
        texto = self.vision.leer_texto_en_pantalla(captura)
        self.logger.debug("--- Fase: Observar (Fin) ---")
        return {'captura': captura, 'texto': texto}

    def pensar(self, estado_observado: dict):
        self.logger.debug("--- Fase: Pensar (Inicio) ---")
        if not self.objetivo:
            self.logger.warning("Pensar: No hay objetivo, finalizando.")
            return {"accion": "finalizar", "params": {"razon": "No hay objetivo"}}
        resumen_memoria = self.memoria.resumir_y_consultar(session_key=self.mi_id_ventana)
        contexto_actual = detectar_contexto_actual()
        prompt = self._construir_prompt(
            resumen_memoria=resumen_memoria,
            feedback_anterior=self.resultado_accion_anterior
        )
        decision = self._call_model(prompt, estado_observado['captura'])
        self.logger.debug("--- Fase: Pensar (Fin) ---")
        return decision
    def _construir_prompt(self, resumen_memoria: str, feedback_anterior=None):
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

ACCIONES COMPUESTAS DISPONIBLES (abstracciones de alto nivel):
- navegar_a_url: {{ "accion": "navegar_a_url", "params": {{ "url": "<url_a_visitar>" }} }}
- buscar_en_google: {{ "accion": "buscar_en_google", "params": {{ "query": "<texto_a_buscar>" }} }}

ACCIONES ATÓMICAS DISPONIBLES (para ser ejecutadas por controlador.py):
- clic: {{ "accion": "clic", "params": {{ "x_rel": <float>, "y_rel": <float> }} }} (Coordenadas relativas 0.0-1.0)
- escribir: {{ "accion": "escribir", "params": {{ "texto": "<texto_a_escribir>" }} }}
- presionar_tecla: {{ "accion": "presionar_tecla", "params": {{ "tecla": "<nombre_tecla>" }} }} (Ej: 'enter', 'escape', 'tab', 'win', 'alt', 'f4')
- scroll: {{ "accion": "scroll", "params": {{ "direccion": "arriba"|"abajo", "clics": <int> }} }}
- cambiar_ventana: {{ "accion": "cambiar_ventana", "params": {{ "tabs": <int> }} }} (Número de veces que presionar TAB con ALT)
- esperar: {{ "accion": "esperar", "params": {{ "segundos": <float> }} }}

ACCIONES DE COMUNICACIÓN (para interactuar con el usuario o finalizar):
- hablar: {{ "accion": "hablar", "params": {{ "mensaje": "<mensaje_para_el_usuario>" }} }}
- finalizar: {{ "accion": "finalizar", "params": {{ "razon": "<razon_de_finalizacion>" }} }}

TAREA PRINCIPAL:
Analiza la pantalla, el objetivo y el feedback para decidir la *siguiente acción* más apropiada, ya sea compuesta, atómica o de comunicación.
Si el objetivo actual puede ser satisfecho completamente con una respuesta verbal o si el usuario te pide explícitamente que "hables" o "respondas hablando", debes priorizar la acción "hablar". Si la tarea ha sido completada y solo necesitas informar, usa la acción "finalizar".

RESPUESTA (ÚNICAMENTE JSON con la siguiente estructura obligatoria):
{{
  "pensamiento": "<Tu razonamiento para elegir esta acción. Describe tu plan paso a paso para lograr el objetivo, y por qué esta acción es la siguiente más lógica.емой>"
  "accion": "<nombre_de_la_accion>",
  "params": {{ "<nombre_param>": "<valor_param>" }}
}}
'''
        return prompt

    def ejecutar_decision(self, decision: dict) -> tuple[bool, bool]:
        """
        Enruta y ejecuta la acción decidida por el modelo.
        Devuelve una tupla (finalizar_bucle, continuar_bucle).
        """
        accion = decision.get("accion")
        params = decision.get("params", {})
        self.logger.info(f"Ejecutando decisión: Acción='{accion}', Params={params}")

        if self.parada_emergencia.is_set():
            self.logger.warning("Acción no ejecutada debido a parada de emergencia.")
            self.resultado_accion_anterior = {'exito': False, 'razon': 'Parada de emergencia activada.'}
            return True, False # Finalizar, no continuar

        # --- Forzar 'finalizar' si el pensamiento indica tarea completada ---
        pensamiento = decision.get("pensamiento", "").lower()
        if ("tarea completada" in pensamiento or "objetivo alcanzado" in pensamiento) and accion != "finalizar":
            self.logger.info("Pensamiento indica tarea completada, forzando acción 'finalizar'.")
            accion = "finalizar"
            params = {"razon": "Tarea completada según el pensamiento del agente."}
            decision = {"accion": accion, "params": params}
        # --- Fin ---

        if not accion:
            self.resultado_accion_anterior = {'exito': False, 'razon': decision.get('razon', 'El modelo no devolvió una acción.')}
            self.logger.error(self.resultado_accion_anterior['razon'])
            return False, True # No finalizar, continuar

        # Definir categorías de acciones
        acciones_comunicacion = ["pedir_aclaracion", "hablar", "proponer_aprendizaje", "finalizar"]
        acciones_compuestas = ["navegar_a_url", "buscar_en_google"]
        
        resultado_ejecucion = None
        
        try:
            if accion in acciones_comunicacion:
                resultado_ejecucion = self._ejecutar_accion_comunicacion(decision)
                if accion == "finalizar":
                    return True, False # Finalizar, no continuar
            
            elif accion in acciones_compuestas:
                resultado_ejecucion = self._ejecutar_accion_compuesta(accion, params)
            
            else: # Asumir acción atómica por defecto
                resultado_ejecucion = self._ejecutar_accion_primitiva(accion, params)

            # Verificación post-acción para acciones no comunicativas
            if accion not in acciones_comunicacion:
                estado_observado_despues = self.observar()
                self.resultado_accion_anterior = self._verificar_paso(estado_observado_despues, decision, resultado_ejecucion)
            else:
                self.resultado_accion_anterior = resultado_ejecucion

            # Para pruebas, podemos forzar la salida después de una acción exitosa
            if self.resultado_accion_anterior['exito'] and accion not in acciones_comunicacion:
                 self.logger.debug(f"Acción '{accion}' ejecutada y verificada con éxito. Finalizando ciclo para la prueba.")
                 return True, False # Finalizar, no continuar

        except Exception as e:
            self.logger.error(f"Excepción no controlada durante la ejecución de la decisión '{accion}': {e}", exc_info=True)
            self.resultado_accion_anterior = {'exito': False, 'razon': f"Excepción no controlada en la ejecución: {e}"}

        return False, True # No finalizar, continuar


    def _ejecutar_accion_primitiva(self, accion: str, params: dict):
        self.logger.debug(f"--- Ejecutando Acción Primitiva: {accion} (Inicio) ---")
        try:
            if accion == "clic":
                ancho, alto = pyautogui.size()
                x_abs = int(params.get('x_rel', 0.5) * ancho)
                y_abs = int(params.get('y_rel', 0.5) * alto)
                self.controlador.clic(x_abs, y_abs)
                self.logger.debug(f"Acción primitiva 'clic' ejecutada en ({x_abs}, {y_abs}).")
            elif accion == "escribir":
                self.controlador.escribir(params.get('texto', ''))
                self.logger.debug(f"Acción primitiva 'escribir' ejecutada con texto: '{params.get('texto', '')}'.")
            elif accion == "presionar_tecla":
                self.controlador.presionar_tecla(params.get('tecla', ''))
                self.logger.debug(f"Acción primitiva 'presionar_tecla' ejecutada con tecla: '{params.get('tecla', '')}'.")
            elif accion == "scroll":
                clics = params.get('clics', 0)
                direccion = params.get('direccion')
                if direccion == "abajo":
                    clics = -clics
                self.controlador.scroll(clics)
                self.logger.debug(f"Acción primitiva 'scroll' ejecutada con clics: '{clics}'.")
            elif accion == "arrastrar_barra":
                self.controlador.arrastrar_barra(params.get('direccion'), params.get('porcentaje'))
                self.logger.debug(f"Acción primitiva 'arrastrar_barra' ejecutada con dirección: '{params.get('direccion')}' y porcentaje: '{params.get('porcentaje')}'.")
            elif accion == "cambiar_ventana":
                self.controlador.mantener_tecla('alt')
                for _ in range(params.get('tabs', 1)):
                    self.controlador.presionar_tecla('tab')
                    self.controlador.esperar(0.2)
                self.controlador.soltar_tecla('alt')
                self.logger.debug(f"Acción primitiva 'cambiar_ventana' ejecutada con tabs: '{params.get('tabs', 1)}'.")
            elif accion == "esperar":
                self.controlador.esperar(params.get('segundos', 1))
                self.logger.debug(f"Acción primitiva 'esperar' ejecutada con segundos: '{params.get('segundos', 1)}'.")
            else:
                self.logger.warning(f"Acción primitiva '{accion}' desconocida.")
                self.logger.debug(f"--- Ejecutando Acción Primitiva: {accion} (Fin - Desconocida) ---")
                return {'exito': False, 'razon': f"Acción '{accion}' no reconocida."} 
            self.logger.debug(f"--- Ejecutando Acción Primitiva: {accion} (Fin - Éxito) ---")
            return {'exito': True, 'razon': f"Acción '{accion}' ejecutada."} 
        except Exception as e:
            self.logger.error(f"ERROR al ejecutar la acción primitiva '{accion}': {e}", exc_info=True)
            self.logger.debug(f"--- Ejecutando Acción Primitiva: {accion} (Fin - Error) ---")
            return {'exito': False, 'razon': f"Excepción al ejecutar '{accion}': {e}"}

    def stream_run(self):
        self.logger.info("--- stream_run (Inicio) ---")
        if not self.operativo or not self.objetivo:
            self.logger.error("stream_run: Agente no operativo o sin objetivo. Saliendo.")
            self.logger.info("--- stream_run (Fin - No operativo/sin objetivo) ---")
            return
        self.logger.info(f"--- INICIANDO BUCLE DE EJECUCIÓN para: '{self.objetivo}' ---")
        max_intentos = 5
        intentos = 0
        while intentos < max_intentos:
            self.logger.debug(f"stream_run: Inicio de ciclo. Intento {intentos+1}/{max_intentos}.")
            if self.parada_emergencia.is_set():
                self.logger.warning("Bucle de ejecución interrumpido por parada de emergencia.")
                self.comunicador.hablar("Proceso detenido por el usuario.")
                break
            if self.esperando_respuesta_usuario:
                self.logger.info("Agente en espera de la respuesta del usuario. Pausando bucle.")
                time.sleep(1)
                continue # Usar continue para re-evaluar la condición en el siguiente ciclo

            intentos += 1
            self.logger.info(f"--- Ciclo de Ejecución: Intento {intentos}/{max_intentos} ---")

            estado_observado = self.observar()
            decision = self.pensar(estado_observado)

            lock_manager.acquire_lock(self.mi_id_ventana)
            try:
                finalizar_bucle, continuar_bucle = self.ejecutar_decision(decision)
                if finalizar_bucle:
                    break
                if not continuar_bucle:
                    time.sleep(1) # Pausa si no se debe continuar inmediatamente
                    continue
            finally:
                lock_manager.release_lock(self.mi_id_ventana)

            time.sleep(1) # Pequeña pausa entre acciones

        if intentos >= max_intentos:
            self.logger.error("Se alcanzó el número máximo de intentos.")
        self.logger.info("--- BUCLE DE EJECUCIÓN FINALIZADO ---")
        self.comunicador.finalizar_habla()
        self.logger.info("--- stream_run (Fin) ---")

    def _ejecutar_accion_comunicacion(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        mensaje = ""
        self.logger.debug(f"_ejecutar_accion_comunicacion (Inicio): Acción {accion}, Params {params}")
        if accion in ["pedir_aclaracion", "hablar"]:
            mensaje = params.get('pregunta', params.get('mensaje', 'No sé qué decir.'))
            self.comunicador.hablar(mensaje)
            self.esperando_respuesta_usuario = True
            self.logger.debug(f"_ejecutar_accion_comunicacion: Hablando: {mensaje}")
        elif accion == "proponer_aprendizaje":
            nombre_habilidad = params.get('nombre_habilidad', 'habilidad_desconocida')
            descripcion = params.get('descripcion', 'Sin descripción.')
            self.estado_agente['esperando_aprobacion'] = True
            self.estado_agente['propuesta_aprendizaje'] = params
            mensaje = f"He identificado una posible nueva habilidad: '{nombre_habilidad}' ({descripcion}). ¿Quieres que la guarde?"
            self.comunicador.hablar(mensaje)
            self.logger.debug(f"_ejecutar_accion_comunicacion: Proponiendo aprendizaje: {nombre_habilidad}")
        elif accion == "finalizar":
            mensaje = params.get('razon', 'He completado la tarea.')
            self.comunicador.hablar(f"Finalizando: {mensaje}")
            self.logger.debug(f"_ejecutar_accion_comunicacion: Finalizando con razón: {mensaje}")
        if mensaje:
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})
        
        resultado = {'exito': True, 'razon': f"Acción de comunicación '{accion}' ejecutada."}
        self.logger.debug(f"_ejecutar_accion_comunicacion (Fin): Resultado {resultado}")
        return resultado

    def _ejecutar_accion_compuesta(self, accion: str, params: dict) -> dict:
        self.logger.debug(f"--- Ejecutando Acción Compuesta: {accion} (Inicio) ---")
        resultado = {'exito': False, 'razon': f"Acción compuesta '{accion}' no implementada."}

        if accion == "navegar_a_url":
            url = params.get("url")
            if url:
                self.logger.info(f"Navegando a URL: {url}")
                # Simular la navegación: escribir la URL y presionar enter
                self.controlador.escribir(url)
                self.controlador.presionar_tecla('enter')
                self.controlador.esperar(2) # Esperar a que la página cargue
                resultado = {'exito': True, 'razon': f"Navegado a {url}."}
            else:
                resultado = {'exito': False, 'razon': "Parámetro 'url' faltante para navegar_a_url."}
        elif accion == "buscar_en_google":
            query = params.get("query")
            if query:
                self.logger.info(f"Buscando en Google: {query}")
                # Simular búsqueda: escribir la query y presionar enter
                self.controlador.escribir(query)
                self.controlador.presionar_tecla('enter')
                self.controlador.esperar(3) # Esperar resultados de búsqueda
                resultado = {'exito': True, 'razon': f"Búsqueda de '{query}' en Google realizada."}
            else:
                resultado = {'exito': False, 'razon': "Parámetro 'query' faltante para buscar_en_google."}
        else:
            self.logger.warning(f"Acción compuesta '{accion}' desconocida.")
            resultado = {'exito': False, 'razon': f"Acción compuesta '{accion}' no reconocida."}
        
        self.logger.debug(f"--- Ejecutando Acción Compuesta: {accion} (Fin) - Resultado: {resultado} ---")
        return resultado

    def _verificar_paso(self, estado_observado_despues: dict, decision_accion: dict, resultado_ejecucion: dict) -> dict:
        self.logger.debug(f"--- Verificando Paso: {decision_accion.get('accion')} (Inicio) ---")
        
        if not resultado_ejecucion['exito']:
            self.logger.warning(f"La acción primitiva falló durante la ejecución: {resultado_ejecucion['razon']}")
            return resultado_ejecucion # Si la ejecución ya falló, no hay nada que verificar.

        accion_verificada = decision_accion.get("accion")
        params_accion = decision_accion.get("params", {})
        
        # Implementación de verificación más sofisticada
        if accion_verificada == "escribir":
            texto_esperado = params_accion.get("texto", "")
            # estado_observado_despues['texto'] es una lista de bloques de texto
            textos_en_pantalla = " ".join([b['texto'] for b in estado_observado_despues.get("texto", [])])
            if texto_esperado and texto_esperado in textos_en_pantalla:
                self.logger.info(f"Verificación exitosa para 'escribir': Texto '{texto_esperado}' encontrado en pantalla.")
                return {'exito': True, 'razon': f"Texto '{texto_esperado}' encontrado."}
            else:
                self.logger.warning(f"Verificación fallida para 'escribir': Texto '{texto_esperado}' NO encontrado en pantalla.")
                return {'exito': False, 'razon': f"Texto '{texto_esperado}' NO encontrado."}
        
        elif accion_verificada in ["scroll", "arrastrar_barra"]:
            # Para scroll/arrastrar, verificamos si el contenido de la pantalla ha cambiado significativamente.
            # Esto es una verificación muy básica y podría mejorarse con un hash de la imagen o un análisis más profundo.
            # Por ahora, asumimos que si la acción se ejecutó sin error, y hay algún texto en pantalla, es un éxito.
            if estado_observado_despues.get("texto"):
                self.logger.info(f"Verificación exitosa para '{accion_verificada}': Contenido de pantalla detectado después del scroll.")
                return {'exito': True, 'razon': f"Contenido de pantalla detectado después de '{accion_verificada}'."}
            else:
                self.logger.warning(f"Verificación básica fallida para '{accion_verificada}': No se detectó contenido en pantalla después del scroll.")
                return {'exito': False, 'razon': f"No se detectó contenido en pantalla después de '{accion_verificada}'."}

        # Para otras acciones, asumimos éxito si la ejecución primitiva no reportó un fallo.
        self.logger.info(f"Verificación de paso '{accion_verificada}' asumida como exitosa (ejecución primitiva exitosa).")
        return {'exito': True, 'razon': f"Verificación básica de '{accion_verificada}'."}


    def _publicar_estado(self, decision: dict, estado_bucle: str): pass

if __name__ == '__main__':
    # Bloque de prueba para verificar la nueva lógica de ejecución de decisiones
    print("--- INICIANDO PRUEBA DE EJECUCIÓN DE DECISIONES ---")

    # Mock simple para el proveedor de modelo, no se usará en esta prueba
    class MockModelProvider:
        def set_model(self, model_name): pass
        def generate_content(self, prompt, image): return {}

    # Callback simple para simular la GUI
    def hablar_test(mensaje):
        print(f"\n[TEST][HABLAR] El agente dice: '{mensaje}'\n")

    # Configurar logging para la prueba
    setup_logging()
    
    # Crear instancia del agente para la prueba
    # No pasamos un proveedor de modelo real, ya que no llamaremos a pensar()
    agente_test = Agente(
        model_provider=MockModelProvider(), 
        model_name="test-model",
        id_ventana="test-suite",
        callback_hablar=hablar_test
    )

    # --- Prueba 1: Acción de Hablar ---
    print("\n--- Prueba 1: Ejecutando acción 'hablar' ---")
    decision_hablar = {
        "pensamiento": "El usuario necesita ser informado.",
        "accion": "hablar",
        "params": {"mensaje": "Esta es una prueba de la acción de hablar."}
    }
    agente_test.ejecutar_decision(decision_hablar)
    print("--- Fin Prueba 1 ---")

    # --- Prueba 2: Acción de Clic ---
    print("\n--- Prueba 2: Ejecutando acción 'clic' ---")
    print("(Se registrará un mensaje de depuración si el controlador es llamado)")
    decision_clic = {
        "pensamiento": "Necesito hacer clic en el centro de la pantalla.",
        "accion": "clic",
        "params": {"x_rel": 0.5, "y_rel": 0.5}
    }
    # Mockear la observación para que no falle
    agente_test.observar = lambda: {'captura': None, 'texto': []} 
    agente_test.ejecutar_decision(decision_clic)
    print("--- Fin Prueba 2 ---")

    # --- Prueba 3: Acción de Escribir ---
    print("\n--- Prueba 3: Ejecutando acción 'escribir' ---")
    decision_escribir = {
        "pensamiento": "Voy a escribir un saludo.",
        "accion": "escribir",
        "params": {"texto": "Hola Mundo"}
    }
    agente_test.ejecutar_decision(decision_escribir)
    print("--- Fin Prueba 3 ---")
    
    # --- Prueba 4: Acción Desconocida ---
    print("\n--- Prueba 4: Ejecutando acción 'inexistente' ---")
    decision_desconocida = {
        "pensamiento": "Intentaré algo que no existe.",
        "accion": "inexistente",
        "params": {}
    }
    agente_test.ejecutar_decision(decision_desconocida)
    print("--- Fin Prueba 4 ---")

    # --- Prueba 5: Finalizar ---
    print("\n--- Prueba 5: Ejecutando acción 'finalizar' ---")
    decision_finalizar = {
        "pensamiento": "La tarea ha terminado.",
        "accion": "finalizar",
        "params": {"razon": "Prueba completada."}
    }
    agente_test.ejecutar_decision(decision_finalizar)
    print("--- Fin Prueba 5 ---")

    print("\n--- PRUEBAS DE EJECUCIÓN FINALIZADAS ---")