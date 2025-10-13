import time
import json
import google.generativeai as genai
from PIL import Image
import pyautogui
import logging
import threading

# Módulos de la aplicación
import config
from controlador import Controlador
from vision import Vision
from knowledge_base import KnowledgeBase
from memoria_chat_mongodb import MongoDBChatMemory
from logger_config import setup_logging
from comunicador import Comunicador
import lock_manager

# Lock global para serializar las llamadas a la API de Gemini y evitar cruces
gemini_api_lock = threading.Lock()

class Agente:
    """
    El agente principal que orquesta los módulos de percepción, decisión y acción.
    """
    def __init__(self, id_ventana=None, id_objetivo=None, callback_hablar=None, callback_finalizar=None):
        setup_logging()
        self.logger = logging.getLogger("InteractIA")
        self.logger.info(f"Inicializando el agente InteractIA (ID: {id_ventana})...")
        
        self.mi_id_ventana = id_ventana
        self.modo = 'autonomo'
        self.titulo_objetivo = None

        if id_objetivo:
            self.modo = 'controlador'
            self.titulo_objetivo = f"interactia-{id_objetivo}"
            self.logger.info(f"Agente en modo 'controlador'. Objetivo: {self.titulo_objetivo}")

        if not config.verificar_configuracion():
            self.operativo = False
            self.logger.error("El agente no puede operar debido a una configuración faltante.")
            return

        # 1. Inicializar el modelo de IA primero
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.modelo = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
            self.logger.info("Modelo de IA configurado exitosamente.")
            self.operativo = True
        except Exception as e:
            self.logger.error(f"ERROR al configurar el modelo de IA: {e}")
            self.operativo = False
            return

        # 2. Inicializar los módulos principales, pasando el modelo a la memoria
        self.controlador = Controlador()
        self.vision = Vision()
        self.kb = KnowledgeBase()
        self.memoria = MongoDBChatMemory(modelo=self.modelo)
        self.comunicador = Comunicador(callback_hablar, callback_finalizar)
        
        self.objetivo = None
        self.historial_acciones = []
        
        # 3. Cargar el historial de conversación desde la base de datos al iniciar
        historial_complejo = self.memoria._recuperar_historial_crudo(
            session_key=self.mi_id_ventana
        ) if self.memoria.operativo else []
        self.historial_conversacion = self.memoria.convertir_historial_a_formato_simple(historial_complejo)
        
        self.estado_agente = {}

        # 4. Cargar habilidades fundamentales
        self.habilidades_fundamentales = self.kb.conocer_habilidad('habilidades_fundamentales_agente')
        if not self.habilidades_fundamentales:
            self.logger.critical("¡ERROR CRÍTICO! No se pudieron cargar las habilidades fundamentales del agente desde la KB.")
            self.operativo = False
            return
        else:
            self.logger.info("Habilidades fundamentales del agente cargadas correctamente desde la KB.")

    def establecer_objetivo(self, objetivo):
        # Comprobar si es un comando interno para el agente
        if objetivo.strip().lower() == '/aprender_de_historial':
            self.logger.info("Comando de meta-aprendizaje recibido. Iniciando ciclo...")
            # Iniciar el ciclo en un nuevo hilo para no bloquear la GUI
            import threading
            threading.Thread(target=self.iniciar_ciclo_meta_aprendizaje).start()
            return

        self.objetivo = objetivo
        # El historial de acciones se reinicia, pero el de conversación persiste en la sesión
        if not self.estado_agente.get('esperando_aprobacion'):
            self.historial_acciones = []

        # Guardar en la base de datos y luego añadir a la lista local
        rol = 'usuario'
        contenido = {'texto': objetivo, 'adjunto': None} # Estructura para futuros adjuntos
        self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
        self.historial_conversacion.append({'rol': rol, 'contenido': objetivo})

        self.logger.info(f"Objetivo establecido y guardado en memoria: {self.objetivo}")

    def observar(self):
        self.logger.info("--- Fase: Observar ---")
        return self.vision.capturar_entorno(id_ventana_propia=self.mi_id_ventana), None

    def pensar(self, captura_entorno: Image.Image, captura_objetivo: Image.Image):
        self.logger.info("--- Fase: Pensar ---")
        if not self.objetivo:
            return {"accion": "finalizar", "params": {"razon": "No hay objetivo"}}

        # Comprobar si estamos esperando la aprobación de una habilidad de meta-aprendizaje
        if self.estado_agente.get('esperando_aprobacion_meta'):
            oportunidad = self.estado_agente.get('oportunidad_en_revision')
            self.estado_agente = {} # Limpiar estado

            if self.objetivo.lower().strip() in ['sí', 'si', 's', 'ok', 'vale']:
                self.logger.info(f"Aprobación de hipótesis recibida para la oportunidad {oportunidad['oportunidad_id']}")
                self.memoria.actualizar_estado_oportunidad(oportunidad['oportunidad_id'], 'verificacion_exitosa')
                return {"accion": "hablar", "params": {"mensaje": "¡Genial! He validado esa habilidad. La procesaré más adelante para formalizarla."}}
            else:
                self.logger.info(f"Rechazo de hipótesis para la oportunidad {oportunidad['oportunidad_id']}")
                self.memoria.actualizar_estado_oportunidad(oportunidad['oportunidad_id'], 'rechazada_por_usuario')
                return {"accion": "hablar", "params": {"mensaje": "Entendido. Descarto esa habilidad potencial."}}

        if self.estado_agente.get('esperando_aprobacion'):
            return self._manejar_aprobacion_aprendizaje()

        # 1. Obtener contexto resumiendo la memoria
        resumen_memoria = self.memoria.resumir_y_consultar(session_key=self.mi_id_ventana)

        # 2. Buscar conocimiento relevante en la KB (solo para modo autónomo)
        habilidad_conocida = None
        if self.modo == 'autonomo':
            habilidad_conocida = self.kb.conocer_habilidad(self.objetivo)

        # 3. Construir el prompt con el contexto de memoria y KB
        prompt = self._construir_prompt(resumen_memoria=resumen_memoria, habilidad=habilidad_conocida)
        
        self.logger.debug(f"--- PROMPT PARA EL MODELO ---\n{prompt}")
        return self.llm_call(prompt, captura_entorno, captura_objetivo)

    def _manejar_aprobacion_aprendizaje(self):
        habilidad_destilada = self.estado_agente.get('habilidad_destilada')
        self.estado_agente = {} # Limpiar estado

        if self.objetivo.lower().strip() in ['sí', 'si', 's', 'ok', 'vale']:
            self.logger.info(f"Aprobación de aprendizaje recibida para la habilidad: {habilidad_destilada['nombre_habilidad']}")
            
            datos_habilidad = habilidad_destilada
            datos_habilidad['origen'] = 'conversacion_usuario_destilado'
            datos_habilidad['validado'] = False

            self.kb.aprender_habilidad(
                nombre_recurso=habilidad_destilada['nombre_habilidad'],
                tipo_recurso='Usuario Destilado',
                datos_habilidad=datos_habilidad
            )
            mensaje = f"Entendido. He aprendido la nueva habilidad '{habilidad_destilada['nombre_habilidad']}'."
            
            # Guardar en la base de datos y luego añadir a la lista local
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})

            return {"accion": "hablar", "params": {"mensaje": mensaje}}
        else:
            self.logger.info("El usuario ha rechazado la propuesta de aprendizaje.")
            mensaje = "De acuerdo, no guardaré la habilidad. ¿Cuál es la siguiente tarea?"
            
            # Guardar en la base de datos y luego añadir a la lista local
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})

            return {"accion": "hablar", "params": {"mensaje": mensaje}}

    def _construir_prompt(self, resumen_memoria: str, habilidad=None):
        es_modo_controlador = self.modo == 'controlador'

        acciones_disponibles_str = ""
        if self.habilidades_fundamentales and 'datos' in self.habilidades_fundamentales and 'acciones' in self.habilidades_fundamentales['datos']:
            for accion in self.habilidades_fundamentales['datos']['acciones']:
                # En modo controlador, las acciones principales son para comunicarse.
                if es_modo_controlador and accion['nombre'] not in ['escribir', 'hablar', 'finalizar']:
                    continue
                acciones_disponibles_str += f"- `{accion['nombre']}`: {accion.get('params', '{}')} ({accion.get('descripcion', '')})\n"

        if es_modo_controlador:
            habilidad_supervisor = self.kb.conocer_habilidad('entrenamiento_supervisado')
            protocolo_supervisor = "Error: No se encontró el protocolo de supervisión en la KB."
            if habilidad_supervisor and 'datos' in habilidad_supervisor and 'descripcion' in habilidad_supervisor['datos']:
                 protocolo_supervisor = habilidad_supervisor['datos']['descripcion']

            prompt = f"""
Tu rol es InteractIA-Supervisor, un agente de IA que enseña a otro agente de IA (el 'controlado') a completar una tarea.

OBJETIVO ACTUAL: Enseñar al agente controlado a completar la tarea: '{self.objetivo}'

PROTOCOLO DE SUPERVISIÓN OBLIGATORIO:
{protocolo_supervisor}

CONTEXTO DE MEMORIA RELEVANTE (Tu conversación con el usuario que te supervisa a ti):
{resumen_memoria}

TAREA PRINCIPAL:
Tu única función es generar el siguiente prompt para el agente controlado. Sigue tu protocolo estrictamente.
1.  **Analiza**: Observa la pantalla del controlado (incluida en la imagen) y tu conversación con el usuario.
2.  **Decide**: Formula el siguiente prompt para el controlado. Puede ser un paso en la tarea, una corrección o una pregunta para guiarle.
3.  **Actúa**: Tu acción DEBE ser `escribir` o `hablar`, y el contenido será el prompt para el controlado. Si la tarea ha terminado, usa `finalizar`.

HERRAMIENTAS DE SUPERVISOR (Simplificadas):
{acciones_disponibles_str}
RESPUESTA (ÚNICAMENTE JSON con la acción 'escribir', 'hablar' o 'finalizar'):
"""
            return prompt

        else: # Modo Autónomo (lógica original)
            contexto_habilidad = f"CONTEXTO DE CONOCIMIENTO PREVIO:\n{json.dumps(habilidad['datos'], indent=2, ensure_ascii=False)}" if habilidad else ""

            prompt = f"""
Tu rol es InteractIA, un agente de IA que completa tareas controlando un ordenador.

OBJETIVO ACTUAL: '{self.objetivo}'

CONTEXTO DE MEMORIA RELEVANTE:
{resumen_memoria}

{contexto_habilidad}

TAREA PRINCIPAL:
Tu deber es analizar el objetivo y el contexto de memoria para crear un plan de acción. Luego, determina el siguiente paso atómico para avanzar en ese plan.
1.  **Analiza y Planifica**: Observa la pantalla y el contexto. Si no tienes un plan, créalo ahora.
2.  **Decide la Próxima Acción**: Basado en tu plan y la imagen, elige la siguiente acción.
3.  **Pide Aclaración si es Necesario**: Si te falta información, usa `pedir_aclaracion` para hacer una pregunta específica.
4.  **Reflexiona y Propón Aprendizaje**: Si finalizas una tarea con éxito y crees que el procedimiento es nuevo y reutilizable, tu acción final DEBE ser `proponer_aprendizaje`.

HABILIDADES FUNDAMENTALES (Tus herramientas):
{acciones_disponibles_str}
RESPUESTA (ÚNICAMENTE JSON):
"""
            return prompt

    def llm_call(self, prompt: str, captura_entorno: Image.Image, captura_objetivo: Image.Image):
        self.logger.info("Esperando el bloqueo de la API de Gemini...")
        with gemini_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                contenido = [prompt, captura_entorno]
                respuesta = self.modelo.generate_content(contenido)
                self.logger.debug(f"Respuesta cruda del modelo: {respuesta.text}")

                json_text = respuesta.text.strip().replace('```json', '').replace('```', '')
                decision = json.loads(json_text)

                if not isinstance(decision, dict) or 'accion' not in decision:
                    for key, value in decision.items():
                        if key in [a['nombre'] for a in self.habilidades_fundamentales['datos']['acciones']]:
                            self.logger.warning(f"Respuesta JSON mal formada detectada. Auto-corrigiendo a formato estándar.")
                            decision = {"accion": key, "params": value}
                            break
                
                self.logger.info(f"Decisión recibida del modelo: {decision}")
                return decision
            except Exception as e:
                self.logger.error(f"ERROR al llamar al modelo de IA o parsear su respuesta: {e}")
                return {"accion": "finalizar", "params": {"razon": "Error en el módulo de decisión"}}

    def actuar(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        self.logger.info(f"--- Fase: Actuar ({accion}) ---")

        # Lógica especial para el modo controlador (Supervisor)
        if self.modo == 'controlador' and accion in ['escribir', 'hablar']:
            texto_a_escribir = ""
            if isinstance(params, dict):
                texto_a_escribir = params.get('texto', params.get('mensaje', ''))
            else:
                texto_a_escribir = params

            if not texto_a_escribir:
                self.logger.warning("Modo controlador: no hay texto para escribir.")
                return 'CONTINUAR'

            self.logger.info(f"Modo controlador: Intentando escribir en la ventana objetivo '{self.titulo_objetivo}'")
            
            if self.controlador.enfocar_ventana(self.titulo_objetivo):
                self.controlador.esperar(0.5) # Pequeña pausa para que la ventana se active
                captura_ventana = self.vision.capturar_ventana_objetivo(self.titulo_objetivo)
                if captura_ventana:
                    # Buscar el botón "Enviar" para localizar el cuadro de texto
                    elementos = self.vision.leer_texto_en_pantalla(captura_ventana)
                    enviar_button = None
                    for elem in elementos:
                        if "enviar" in elem.get('texto', '').lower():
                            enviar_button = elem
                            break
                    
                    if enviar_button:
                        # Asumimos que el input está a la izquierda del botón "Enviar"
                        # Calculamos el centro del cuadro de texto
                        input_x = enviar_button['left'] - 100 # Un valor estimado a la izquierda
                        input_y = enviar_button['top'] + (enviar_button['height'] // 2)
                        
                        # Las coordenadas de OCR son relativas a la captura de la ventana,
                        # necesitamos hacerlas absolutas a la pantalla.
                        ventanas = pyautogui.getWindowsWithTitle(self.titulo_objetivo)
                        if ventanas:
                            ventana_objetivo = ventanas[0]
                            abs_x = ventana_objetivo.left + input_x
                            abs_y = ventana_objetivo.top + input_y
                            
                            self.controlador.clic(abs_x, abs_y)
                            self.controlador.esperar(0.2)
                            self.controlador.escribir(texto_a_escribir)
                            self.logger.info("Modo controlador: Texto escrito en la ventana objetivo.")
                            # Opcional: presionar Enter o hacer clic en Enviar
                            # self.controlador.presionar_tecla('enter')
                        else:
                            self.logger.error("Modo controlador: Se perdió la ventana objetivo después de encontrar el botón.")

                    else:
                        self.logger.warning("Modo controlador: No se encontró el botón 'Enviar' en la ventana objetivo.")
                else:
                    self.logger.warning("Modo controlador: No se pudo capturar la ventana objetivo después de enfocarla.")
            else:
                self.logger.error(f"Modo controlador: No se pudo enfocar la ventana objetivo '{self.titulo_objetivo}'.")
            
            return 'CONTINUAR' # El supervisor continúa su propio ciclo

        # Lógica original para el modo autónomo
        lock_manager.acquire_lock(self.mi_id_ventana)
        try:
            if accion == "proponer_aprendizaje":
                self._destilar_y_proponer_habilidad()
                return 'DETENER_Y_ESPERAR'
            elif accion in ["pedir_aclaracion", "hablar"]:
                mensaje = ""
                if isinstance(params, dict):
                    mensaje = params.get('pregunta', params.get('mensaje', 'No sé qué decir.'))
                else:
                    mensaje = params
                self.comunicador.hablar(mensaje)
                
                # Guardar en la base de datos y luego añadir a la lista local
                rol = 'agente'
                contenido = {'texto': mensaje, 'adjunto': None}
                self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
                self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})

                self.comunicador.finalizar_habla()
                return 'DETENER_Y_ESPERAR'
            elif accion == "clic":
                ancho, alto = pyautogui.size()
                x_abs = int(params['x_rel'] * ancho)
                y_abs = int(params['y_rel'] * alto)
                self.controlador.clic(x_abs, y_abs)
            elif accion == "escribir":
                texto = params['texto'] if isinstance(params, dict) else params
                self.controlador.escribir(texto)
            elif accion == "presionar_tecla":
                tecla = params['tecla'] if isinstance(params, dict) else params
                self.controlador.presionar_tecla(tecla)
            elif accion == "scroll":
                self.controlador.scroll(params['direccion'], params['clics'])
            elif accion == "arrastrar_barra":
                self.controlador.arrastrar_barra(params['direccion'], params['porcentaje'])
            elif accion == "cambiar_ventana":
                self.controlador.mantener_tecla('alt')
                tabs = params.get('tabs', 1) if isinstance(params, dict) else 1
                for _ in range(tabs):
                    self.controlador.presionar_tecla('tab')
                    self.controlador.esperar(0.2)
                self.controlador.soltar_tecla('alt')
            elif accion == "esperar":
                segundos = params['segundos'] if isinstance(params, dict) else params
                self.controlador.esperar(segundos)
            elif accion == "finalizar":
                razon = params.get('razon', 'Razón no especificada') if isinstance(params, dict) else params
                self.logger.info(f"Finalizando por decisión del modelo. Razón: {razon}")
                return 'FINALIZAR'
            else:
                pregunta = f"La acción '{accion}' no es válida o no sé cómo interpretarla. ¿Podrías darme una instrucción más simple?"
                self.logger.warning(f"Acción desconocida o no manejada: {accion}. Pidiendo aclaración.")
                self.comunicador.hablar(pregunta)
                
                # Guardar en la base de datos y luego añadir a la lista local
                rol = 'agente'
                contenido = {'texto': pregunta, 'adjunto': None}
                self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
                self.historial_conversacion.append({'rol': rol, 'contenido': pregunta})

                self.comunicador.finalizar_habla()
                return 'DETENER_Y_ESPERAR'
            
            self.historial_acciones.append(decision)
            return 'CONTINUAR'

        except Exception as e:
            self.logger.error(f"ERROR al ejecutar la acción '{accion}': {e}")
            return 'FINALIZAR'
        finally:
            lock_manager.release_lock(self.mi_id_ventana)

    def _destilar_y_proponer_habilidad(self):
        self.logger.info("Iniciando el proceso de destilación de conocimiento.")
        historial_str = "\n".join([f"{msg['rol']}: {msg['contenido']}" for msg in self.historial_conversacion])
        
        prompt_destilacion = f"""
        Analiza el siguiente historial de conversación donde un usuario enseñó a un agente a completar una tarea.
        Extrae el objetivo principal y resume los pasos en una habilidad estructurada y reutilizable.

        HISTORIAL DE CONVERSACIÓN:
        {historial_str}

        TAREA:
        Responde ÚNICAMENTE con un JSON que siga esta estructura:
        {{
          "nombre_habilidad": "<un_nombre_corto_y_descriptivo_en_snake_case>",
          "descripcion": "<Una descripción clara de lo que hace la habilidad. >",
          "pasos": [
            {{ "accion": "<nombre_de_la_accion>", "params": {{ "<nombre_param>": "<valor_param>" }} }}
          ]
        }}
        """
        try:
            respuesta = self.modelo.generate_content(prompt_destilacion)
            self.logger.debug(f"Respuesta de destilación cruda: {respuesta.text}")
            json_text = respuesta.text.strip().replace('```json', '').replace('```', '')
            habilidad_destilada = json.loads(json_text)

            nombre = habilidad_destilada.get('nombre_habilidad', 'sin_nombre')
            descripcion = habilidad_destilada.get('descripcion', 'una nueva habilidad')
            pasos_str = "".join([f"  {i+1}. {paso['accion']}: {paso.get('params', {})}\n" for i, paso in enumerate(habilidad_destilada.get('pasos', []))])

            pregunta = f"He aprendido una nueva habilidad: '{descripcion}'.\nLos pasos que he deducido son:\n{pasos_str}¿Es este procedimiento correcto y quieres que lo guarde como la habilidad '{nombre}'? (sí/no)"

            self.estado_agente['esperando_aprobacion'] = True
            self.estado_agente['habilidad_destilada'] = habilidad_destilada
            
            self.comunicador.hablar(pregunta)

            # Guardar en la base de datos y luego añadir a la lista local
            rol = 'agente'
            contenido = {'texto': pregunta, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': pregunta})

            self.comunicador.finalizar_habla()
        except Exception as e:
            self.logger.error(f"Error durante la destilación del conocimiento: {e}")
            self.comunicador.hablar("Tuve un problema al procesar lo que aprendí. Empezaré de nuevo.")
            self.comunicador.finalizar_habla()

    def _publicar_estado(self, decision: dict, estado_bucle: str):
        """Publica el estado actual del agente a la base de datos."""
        if not self.memoria.operativo:
            return

        estado_data = {
            'objetivo_actual': self.objetivo,
            'ultima_decision': decision,
            'estado_bucle': estado_bucle,
            'historial_acciones': self.historial_acciones[-5:] # Publicar las últimas 5 acciones
        }
        self.memoria.publicar_estado_agente(self.mi_id_ventana, estado_data)

    def stream_run(self):
        if not self.operativo or not self.objetivo:
            self.comunicador.hablar("Error: El agente no es operativo o no tiene objetivo.")
            self._publicar_estado({"accion": "finalizar", "params": {"razon": "No operativo o sin objetivo"}}, "ERROR")
            return

        self.logger.info(f"--- INICIANDO BUCLE DE EJECUCIÓN para el objetivo: '{self.objetivo}' ---")
        
        last_progress_time = time.time()
        
        while True:
            self.logger.info("--- Nuevo ciclo de Observar-Pensar-Actuar ---")

            if time.time() - last_progress_time > 25:
                self.logger.warning("El agente no ha progresado en 25 segundos. Pidiendo ayuda.")
                self.comunicador.hablar("Parece que estoy atascado. ¿Puedes darme una pista o un objetivo más simple?")
                self.comunicador.finalizar_habla()
                self._publicar_estado({"accion": "finalizar", "params": {"razon": "Timeout de progreso"}}, "ATASCADO")
                break
            
            captura_entorno, _ = self.observar()
            decision = self.pensar(captura_entorno, None)
            self._publicar_estado(decision, "PENSANDO")

            if decision.get("accion") in ["pedir_aclaracion", "hablar", "proponer_aprendizaje", "finalizar"]:
                last_progress_time = time.time()
            
            resultado_actuar = self.actuar(decision)

            if resultado_actuar == 'FINALIZAR':
                params = decision.get('params', {})
                razon = "Acción fallida o finalizada"
                if isinstance(params, dict):
                    razon = params.get('razon', 'Razón no especificada')
                elif isinstance(params, str):
                    razon = params
                self.logger.info(f"Agente finalizando el bucle de ejecución. Razón: {razon}")
                self._publicar_estado(decision, "FINALIZADO")
                break
            elif resultado_actuar == 'DETENER_Y_ESPERAR':
                self.logger.info("Agente en espera de la respuesta del usuario.")
                self._publicar_estado(decision, "ESPERANDO_USUARIO")
                break
            
            time.sleep(1)
        
        self.logger.info("--- BUCLE DE EJECUCIÓN FINALIZADO ---")

    # --- MÉTODOS DEL CICLO DE META-APRENDIZAJE ---

    def iniciar_ciclo_meta_aprendizaje(self):
        """Orquesta las fases de descubrimiento y procesamiento de conocimiento pasado."""
        self.comunicador.hablar("Iniciando ciclo de meta-aprendizaje. Buscaré conocimiento útil en conversaciones pasadas.")
        self.comunicador.finalizar_habla()

        # Fase 1: Descubrir nuevas oportunidades en chats sin analizar
        self._fase_descubrimiento()

        # Fase 2: Procesar una oportunidad pendiente
        self._fase_procesamiento()

        self.comunicador.hablar("Ciclo de meta-aprendizaje finalizado.")
        self.comunicador.finalizar_habla()

    def _fase_descubrimiento(self):
        """Busca un chat no analizado y extrae todas las habilidades potenciales."""
        self.logger.info("META-APRENDIZAJE: Iniciando Fase de Descubrimiento.")
        session_key_a_analizar = self.memoria.buscar_chat_sin_analizar()

        if not session_key_a_analizar:
            self.logger.info("META-APRENDIZAJE: No hay conversaciones nuevas que analizar.")
            self.comunicador.hablar("No he encontrado conversaciones nuevas para analizar.")
            self.comunicador.finalizar_habla()
            return

        self.comunicador.hablar(f"Analizando la conversación '{session_key_a_analizar}' en busca de habilidades...")
        self.comunicador.finalizar_habla()

        historial_crudo = self.memoria._recuperar_historial_crudo(session_key_a_analizar, limit=500)
        historial_str = "\n".join([f"{msg['role']}: {msg.get('content', {}).get('texto', '')}" for msg in historial_crudo])

        prompt_extraccion = f"""
        Analiza el siguiente historial de conversación y detecta cada procedimiento o tarea discreta que el usuario le enseñó al agente.
        Para cada procedimiento, crea un objeto JSON con una "descripcion" clara y concisa de la habilidad aprendida.
        
        HISTORIAL:
        {historial_str}
        
        RESPUESTA (ÚNICAMENTE JSON), una lista de objetos:
        [ 
            {{ "descripcion": "<Descripción de la primera habilidad potencial>" }},
            {{ "descripcion": "<Descripción de la segunda habilidad potencial>" }}
        ]
        """
        try:
            respuesta = self.modelo.generate_content(prompt_extraccion)
            self.logger.debug(f"Respuesta de extracción de hipótesis: {respuesta.text}")
            json_text = respuesta.text.strip().replace('```json', '').replace('```', '')
            hipotesis = json.loads(json_text)

            if hipotesis and isinstance(hipotesis, list):
                self.memoria.crear_oportunidades_de_aprendizaje(session_key_a_analizar, hipotesis)
                self.comunicador.hablar(f"Análisis completo. He encontrado {len(hipotesis)} posibles nuevas habilidades.")
                self.comunicador.finalizar_habla()
            else:
                self.comunicador.hablar("No encontré habilidades claras en esa conversación.")
                self.comunicador.finalizar_habla()

            # Marcar la sesión como analizada para no repetirla
            self.memoria.marcar_sesion_como_analizada(session_key_a_analizar)

        except Exception as e:
            self.logger.error(f"META-APRENDIZAJE: Error en la fase de descubrimiento: {e}")
            self.comunicador.hablar("Tuve un problema analizando esa conversación.")
            self.comunicador.finalizar_habla()

    def _fase_procesamiento(self):
        """Busca una oportunidad de aprendizaje pendiente y la procesa."""
        self.logger.info("META-APRENDIZAJE: Iniciando Fase de Procesamiento.")
        oportunidad = self.memoria.obtener_oportunidad_pendiente()

        if not oportunidad:
            self.logger.info("META-APRENDIZAJE: No hay oportunidades de aprendizaje pendientes.")
            self.comunicador.hablar("No tengo ninguna habilidad nueva que verificar por ahora.")
            self.comunicador.finalizar_habla()
            return

        oportunidad_id = oportunidad["oportunidad_id"]
        descripcion = oportunidad["descripcion_hipotesis"]
        fuente_session_id = oportunidad["fuente_session_id"]

        # En un futuro, aquí iría el ciclo de verificación autónoma.
        # Por ahora, le preguntamos directamente al usuario si la hipótesis es válida.
        pregunta_verificacion = f"He encontrado una habilidad potencial de una conversación pasada: '{descripcion}'. ¿Crees que esto es una habilidad útil que debería intentar aprender y formalizar? (sí/no)"
        self.comunicador.hablar(pregunta_verificacion)
        self.comunicador.finalizar_habla()

        # Aquí el agente se pone en modo de espera. La respuesta del usuario (sí/no)
        # se procesará en el siguiente ciclo de `establecer_objetivo`.
        self.estado_agente['esperando_aprobacion_meta'] = True
        self.estado_agente['oportunidad_en_revision'] = oportunidad
        self.logger.info(f"Esperando aprobación del usuario para la oportunidad {oportunidad_id}")


if __name__ == '__main__':
    # Esta parte es para pruebas y no se ejecuta desde la GUI
    def main_test():
        agente = Agente(id_ventana="test_agent")
        if agente.operativo:
            agente.establecer_objetivo("abrir notepad y escribir hola mundo")
            agente.stream_run()

    main_test()