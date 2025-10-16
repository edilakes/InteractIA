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
from contexto_manager import detectar_contexto_actual # <-- NUEVA IMPORTACIÓN
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
        self.resultado_accion_anterior = None # Para el ciclo de verificación

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
        self.comunicador = Comunicador(callback_hablar, callback_finalizar)
        
        self.objetivo = None
        self.historial_acciones = []
        
        historial_complejo = self.memoria._recuperar_historial_crudo(
            session_key=self.mi_id_ventana
        ) if self.memoria.operativo else []
        self.historial_conversacion = self.memoria.convertir_historial_a_formato_simple(historial_complejo)
        
        self.estado_agente = {}

        self.habilidades_fundamentales = self.kb.conocer_habilidad('habilidades_fundamentales_agente')
        if not self.habilidades_fundamentales:
            self.logger.critical("¡ERROR CRÍTICO! No se pudieron cargar las habilidades fundamentales.")
            self.operativo = False
        else:
            self.logger.info("Habilidades fundamentales cargadas correctamente.")

    def establecer_objetivo(self, objetivo):
        if objetivo.strip().lower() == '/aprender_de_historial':
            self.logger.info("Comando de meta-aprendizaje recibido.")
            threading.Thread(target=self.iniciar_ciclo_meta_aprendizaje).start()
            return

        self.objetivo = objetivo
        if not self.estado_agente.get('esperando_aprobacion'):
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

        if self.estado_agente.get('esperando_aprobacion'):
            return self._manejar_aprobacion_aprendizaje()

        resumen_memoria = self.memoria.resumir_y_consultar(session_key=self.mi_id_ventana)
        
        # --- LÓGICA DE CONTEXTO MEJORADA ---
        habilidades_para_prompt = []
        if self.modo == 'autonomo':
            # 1. Detectar contexto actual y cargar habilidades relevantes
            contexto_actual = detectar_contexto_actual()
            self.logger.info(f"Contexto de aplicación detectado: {contexto_actual}")
            habilidades_contextuales = self.kb.conocer_habilidades_por_contexto([contexto_actual, "General"])
            habilidades_para_prompt.extend(habilidades_contextuales)
            self.logger.info(f"Cargadas {len(habilidades_contextuales)} habilidades para los contextos '{contexto_actual}' y 'General'.")

            # 2. Mantener la búsqueda semántica como complemento
            habilidad_semantica = self.kb.conocer_habilidad(self.objetivo)
            if habilidad_semantica:
                # Evitar duplicados si la búsqueda semántica encuentra una habilidad ya incluida por contexto
                if not any(h['nombre_recurso'] == habilidad_semantica['nombre_recurso'] for h in habilidades_para_prompt):
                    habilidades_para_prompt.append(habilidad_semantica)
                    self.logger.info(f"Añadida 1 habilidad por búsqueda semántica: '{habilidad_semantica['nombre_recurso']}'.")
        # --- FIN DE LA LÓGICA DE CONTEXTO ---

        prompt = self._construir_prompt(
            resumen_memoria=resumen_memoria, 
            habilidades_contextuales=habilidades_para_prompt, # <-- Parámetro actualizado
            feedback_anterior=self.resultado_accion_anterior
        )
        
        self.logger.debug(f"--- PROMPT PARA EL MODELO ---\n{prompt}")
        return self.llm_call(prompt, estado_observado['captura'], None)

    def _construir_prompt(self, resumen_memoria: str, habilidades_contextuales: list = None, feedback_anterior=None):
        if self.modo == 'controlador':
            # Lógica para modo controlador (sin cambios)
            return ""

        acciones_disponibles_str = "\n".join([
            f"- `{a['nombre']}`: {a.get('params', '{}')} ({a.get('descripcion', '')})"
            for a in self.habilidades_fundamentales['datos']['acciones']
        ])

        # --- LÓGICA DE CONSTRUCCIÓN DE CONTEXTO MEJORADA ---
        contexto_habilidad = ""
        if habilidades_contextuales:
            info_habilidades = []
            for hab in habilidades_contextuales:
                # Extraemos solo la información relevante para no sobrecargar el prompt
                info_relevante = {
                    "nombre": hab.get("nombre_recurso"),
                    "tipo": hab.get("tipo_recurso"),
                    "descripcion": hab.get("datos", {}).get("descripcion"),
                    "acciones_o_atajos": hab.get("datos", {}).get("acciones", hab.get("datos", {}).get("atajos_teclado"))
                }
                info_habilidades.append(json.dumps(info_relevante, indent=2, ensure_ascii=False))
            
            contexto_habilidad = "CONTEXTO DE CONOCIMIENTO DISPONIBLE (Habilidades y Atajos Relevantes):\n" + "\n---\n".join(info_habilidades)
        else:
            contexto_habilidad = "No se encontró conocimiento específico en la base de datos para este objetivo o contexto."
        # --- FIN DE LA LÓGICA DE CONSTRUCCIÓN ---

        contexto_feedback = ""
        if feedback_anterior:
            estado = "ÉXITO" if feedback_anterior['exito'] else "FALLO"
            contexto_feedback = f"RESULTADO DE LA ACCIÓN ANTERIOR: {estado}. Razón: {feedback_anterior['razon']}.\n"
            if not feedback_anterior['exito']:
                contexto_feedback += "Debes re-evaluar y probar un enfoque diferente."

        prompt = f"""
Tu rol es InteractIA, un agente de IA que completa tareas controlando un ordenador.
Tu proceso se basa en un ciclo de **Observar, Pensar, Actuar y Verificar**.

OBJETIVO ACTUAL: '{self.objetivo}'

{contexto_feedback}

CONTEXTO DE MEMORIA RELEVANTE:
{resumen_memoria}

{contexto_habilidad}

TAREA PRINCIPAL:
Tu deber es analizar la pantalla, el objetivo y el feedback para decidir la siguiente acción.

1.  **Analiza y Planifica**: Observa la pantalla y el contexto. Si tu acción anterior falló, crea un plan alternativo.
2.  **Decide la Próxima Acción**: Elige la siguiente acción atómica para avanzar en tu plan.
3.  **Predice el Resultado**: **CRÍTICO**: Debes predecir el resultado observable de tu acción. ¿Qué cambiará en la pantalla? ¿Qué texto nuevo aparecerá?

HABILIDADES FUNDAMENTALES (Tus herramientas):
{acciones_disponibles_str}

RESPUESTA (ÚNICAMENTE JSON con la siguiente estructura obligatoria):
{{
  "pensamiento": "<Tu razonamiento para elegir esta acción y predecir el resultado>",
  "accion": "<nombre_de_la_accion>",
  "params": {{ "<nombre_param>": "<valor_param>" }},
  "resultado_esperado": {{
    "descripcion_visual": "<Describe el cambio visual que esperas ver en la pantalla>",
    "texto_a_buscar": ["<un texto que DEBE aparecer>", "<otro texto que esperas ver>"]
  }}
}}
"""
        return prompt

    def _ejecutar_accion(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        self.logger.info(f"--- Ejecutando Acción: {accion} ---")
        
        lock_manager.acquire_lock(self.mi_id_ventana)
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
                self.logger.warning(f"Acción '{accion}' no es una acción de UI ejecutable directamente.")
                return False # Indica que no es una acción de UI
            
            self.historial_acciones.append(decision)
            return True # Indica que la acción de UI se ejecutó
        except Exception as e:
            self.logger.error(f"ERROR al ejecutar la acción '{accion}': {e}", exc_info=True)
            return False
        finally:
            lock_manager.release_lock(self.mi_id_ventana)

    def actuar_y_percibir(self, decision: dict):
        accion = decision.get("accion")
        self.logger.info(f"--- Fase: Actuar y Percibir ({accion}) ---")

        if not self._ejecutar_accion(decision):
            return None # La acción no se pudo ejecutar o no era de UI

        # Para la Fase 1, solo 'escribir' activa la percepción.
        if accion == "escribir":
            self.logger.info("Acción verificable. Esperando 2s para que la UI se estabilice...")
            time.sleep(2)
            self.logger.info("Percibiendo el estado post-acción.")
            return self.observar()
        else:
            self.logger.info(f"Acción '{accion}' ejecutada sin verificación en esta fase.")
            return None

    def verificar(self, decision: dict, estado_percibido: dict):
        self.logger.info("--- Fase: Verificar ---")
        resultado_esperado = decision.get("resultado_esperado")

        if not resultado_esperado or not estado_percibido:
            razon = "No se pudo verificar la acción (faltaba resultado esperado o estado percibido)."
            self.logger.warning(razon)
            return {'exito': False, 'razon': razon}

        textos_a_buscar = resultado_esperado.get("texto_a_buscar", [])
        if not textos_a_buscar:
            razon = "Acción ejecutada, pero no había criterio de éxito textual para verificar."
            self.logger.info(razon)
            return {'exito': True, 'razon': razon}

        texto_percibido_completo = " ".join([block['texto'] for block in estado_percibido.get('texto', [])])
        self.logger.info(f"Texto completo percibido para verificación: '{texto_percibido_completo}'")

        for texto_buscado in textos_a_buscar:
            palabras_buscadas = texto_buscado.split()
            if not all(palabra in texto_percibido_completo for palabra in palabras_buscadas):
                razon = f"FALLO: El texto esperado '{texto_buscado}' (palabras: {palabras_buscadas}) no fue encontrado en la pantalla."
                self.logger.warning(razon)
                return {'exito': False, 'razon': razon}

        razon = f"ÉXITO: Todos los textos esperados ({textos_a_buscar}) fueron encontrados."
        self.logger.info(razon)
        return {'exito': True, 'razon': razon}

    def stream_run(self):
        if not self.operativo or not self.objetivo:
            self.comunicador.hablar("Error: Agente no operativo o sin objetivo.")
            return

        self.logger.info(f"--- INICIANDO BUCLE DE EJECUCIÓN VERIFICADA para: '{self.objetivo}' ---")
        
        max_intentos = 5 # Para evitar bucles infinitos
        intentos = 0
        while intentos < max_intentos:
            intentos += 1
            self.logger.info(f"--- Ciclo de Ejecución: Intento {intentos}/{max_intentos} ---")

            estado_observado = self.observar()
            decision = self.pensar(estado_observado)
            self._publicar_estado(decision, "PENSANDO")

            accion = decision.get("accion")
            if accion in ["pedir_aclaracion", "hablar", "proponer_aprendizaje", "finalizar"]:
                self.logger.info(f"Ejecutando acción de comunicación: {accion}")
                # Aquí puedes manejar la lógica específica de estas acciones si es necesario
                if accion == "finalizar": break
                self._ejecutar_accion_comunicacion(decision) # Método separado para claridad
                break

            estado_post_accion = self.actuar_y_percibir(decision)

            if estado_post_accion:
                resultado_verificacion = self.verificar(decision, estado_post_accion)
                self.resultado_accion_anterior = resultado_verificacion
            else:
                self.resultado_accion_anterior = {'exito': True, 'razon': f"La acción '{accion}' se ejecutó sin verificación."}
            
            self._publicar_estado(decision, f"VERIFICADO: {'ÉXITO' if self.resultado_accion_anterior['exito'] else 'FALLO'}")
            
            if self.resultado_accion_anterior['exito']:
                self.logger.info("La acción tuvo éxito o no requería verificación. Continuando con el plan.")
                # Aquí podrías decidir si el objetivo está completo y finalizar
            else:
                self.logger.error("La acción ha fallado la verificación. El agente re-evaluará.")

            time.sleep(1)
        
        if intentos >= max_intentos:
            self.logger.error("Se alcanzó el número máximo de intentos. Finalizando el bucle.")

        self.logger.info("--- BUCLE DE EJECUCIÓN FINALIZADO ---")

    def _ejecutar_accion_comunicacion(self, decision: dict):
        accion = decision.get("accion")
        params = decision.get("params", {})
        if accion in ["pedir_aclaracion", "hablar"]:
            mensaje = params.get('pregunta', params.get('mensaje', 'No sé qué decir.'))
            self.comunicador.hablar(mensaje)
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})
            self.comunicador.finalizar_habla()
        elif accion == "proponer_aprendizaje":
            self._destilar_y_proponer_habilidad()

    def llm_call(self, prompt: str, captura_entorno: Image.Image, captura_objetivo: Image.Image):
        self.logger.info("Esperando el bloqueo de la API de Gemini...")
        with gemini_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                contenido = [prompt, captura_entorno]
                respuesta = self.modelo.generate_content(contenido)
                self.logger.debug(f"Respuesta cruda del modelo: {respuesta.text}")

                json_text = respuesta.text.strip().replace('''json', '').replace('''', '')
                decision = json.loads(json_text)
                return decision
            except json.JSONDecodeError as e:
                self.logger.error(f"ERROR al parsear JSON: {e}. Respuesta cruda: '{respuesta.text}'")
                return {"accion": "finalizar", "params": {"razon": "Error de parseo en la respuesta del modelo."}}
            except Exception as e:
                self.logger.error(f"ERROR al llamar al modelo de IA: {e}", exc_info=True)
                return {"accion": "finalizar", "params": {"razon": "Error en el módulo de decisión"}}

    # --- MÉTODOS DE APRENDIZAJE (Sin cambios) ---
    def _manejar_aprobacion_aprendizaje(self):
        pass
    def _destilar_y_proponer_habilidad(self):
        pass
    def _publicar_estado(self, decision: dict, estado_bucle: str):
        pass
    def iniciar_ciclo_meta_aprendizaje(self):
        pass
    def _fase_descubrimiento(self):
        pass
    def _fase_procesamiento(self):
        pass

if __name__ == '__main__':
    def main_test():
        setup_logging(log_level=logging.INFO)
        agente = Agente(id_ventana="test_agent_verificado")
        if agente.operativo:
            try:
                p = subprocess.Popen(["notepad.exe"])
                print("Bloc de notas abierto para la prueba. Esperando 3 segundos...")
                time.sleep(3)
            except FileNotFoundError:
                print("ERROR: No se pudo abrir notepad.exe.")
                return

            agente.establecer_objetivo("Escribe 'Hola Mundo Verificado' en la ventana activa.")
            agente.stream_run()
            p.terminate() # Cerrar notepad al final

    main_test()