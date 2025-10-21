# Paquete de Código Consolidado

---
path: agente.py
---
```py
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
                # Solo incluimos habilidades con implementación o acciones primitivas
                datos = hab.get("datos", {})
                if 'modulo_implementacion' in datos or hab.get("nombre_recurso") == "habilidades_fundamentales_agente":
                    acciones = datos.get("acciones", [])
                    info_relevante = {
                        "nombre_habilidad": hab.get("nombre_recurso"),
                        "descripcion": datos.get("descripcion"),
                        "acciones_disponibles": [{k: v for k, v in a.items() if k != 'params'} for a in acciones]
                    }
                    info_habilidades.append(json.dumps(info_relevante, indent=2, ensure_ascii=False))
            
            contexto_habilidad = "HABILIDADES DISPONIBLES (Herramientas y Conocimiento):\n" + "\n---\n".join(info_habilidades)
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
1.  **Analiza y Planifica**: Observa la pantalla y el contexto. Si tu acción anterior falló, crea un plan alternativo.
2.  **Decide la Próxima Acción**: Elige la siguiente acción o habilidad de alto nivel para avanzar en tu plan. No inventes acciones, usa solo las de la lista.
3.  **Define los Parámetros**: Especifica los parámetros exactos que la acción necesita.

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
        accion = decision.get("accion")
        params = decision.get("params", {})
        self.logger.info(f"--- Ejecutando Habilidad Compleja: {accion} ---")

        # Buscar la habilidad en la KB para encontrar su implementación
        habilidad_doc = self.kb.conocer_habilidad_por_accion(accion)
        if not habilidad_doc or "modulo_implementacion" not in habilidad_doc.get("datos", {}):
            msg = f"No se encontró implementación para la habilidad '{accion}' en la KB."
            self.logger.error(msg)
            return {'exito': False, 'razon': msg}

        modulo_nombre = habilidad_doc["datos"]["modulo_implementacion"]
        self.logger.info(f"Cargando habilidad '{accion}' desde el módulo '{modulo_nombre}'...")

        try:
            # Importar dinámicamente el módulo
            modulo = importlib.import_module(modulo_nombre)
            # Obtener la función a llamar (debe coincidir con el nombre de la acción)
            funcion_habilidad = getattr(modulo, accion)
        except (ImportError, AttributeError) as e:
            msg = f"No se pudo cargar la función '{accion}' desde el módulo '{modulo_nombre}': {e}"
            self.logger.error(msg, exc_info=True)
            return {'exito': False, 'razon': msg}

        # Inyección de dependencias: Pasar instancias del agente a la habilidad si las necesita
        try:
            sig = inspect.signature(funcion_habilidad)
            if 'controlador' in sig.parameters:
                params['controlador'] = self.controlador
            if 'vision' in sig.parameters:
                params['vision'] = self.vision
            if 'kb' in sig.parameters:
                params['kb'] = self.kb
            if 'agente' in sig.parameters:
                params['agente'] = self
        except Exception as e:
            self.logger.warning(f"No se pudo inspeccionar la firma de la función '{accion}': {e}")


        # Ejecutar la función de la habilidad
        try:
            resultado = funcion_habilidad(**params)
            if isinstance(resultado, bool):
                return {'exito': resultado, 'razon': f"La habilidad '{accion}' devolvió: {resultado}"}
            elif isinstance(resultado, dict) and 'exito' in resultado and 'razon' in resultado:
                return resultado
            else:
                return {'exito': True, 'razon': f"Habilidad '{accion}' ejecutada."} 
        except Exception as e:
            msg = f"Excepción al ejecutar la habilidad '{accion}': {e}"
            self.logger.error(msg, exc_info=True)
            return {'exito': False, 'razon': msg}


    def stream_run(self):
        if not self.operativo or not self.objetivo:
            self.comunicador.hablar("Error: Agente no operativo o sin objetivo.")
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
                self.resultado_accion_anterior = {'exito': False, 'razon': 'El modelo no devolvió una acción.'}
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
            # Lógica para proponer aprendizaje
            pass
        elif accion == "finalizar":
            mensaje = params.get('razon', 'Tarea finalizada.')
            self.comunicador.hablar(f"Finalizando: {mensaje}")

        if mensaje:
            rol = 'agente'
            contenido = {'texto': mensaje, 'adjunto': None}
            self.memoria.guardar_mensaje(self.mi_id_ventana, rol, contenido)
            self.historial_conversacion.append({'rol': rol, 'contenido': mensaje})
        
        self.resultado_accion_anterior = {'exito': True, 'razon': f"Acción de comunicación '{accion}' ejecutada."} 


    def llm_call(self, prompt: str, captura_entorno: Image.Image):
        self.logger.info("Esperando el bloqueo de la API de Gemini...")
        with gemini_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                contenido = [prompt, captura_entorno]
                respuesta = self.modelo.generate_content(contenido)
                self.logger.debug(f"Respuesta cruda del modelo: {respuesta.text}")

                # Extraer el bloque JSON usando una expresión regular más robusta
                match = re.search(r'\{.*?\}', respuesta.text, re.DOTALL)
                if match:
                    json_text = match.group(0)
                else:
                    json_text = respuesta.text.strip()

                decision = json.loads(json_text)
                return decision
            except json.JSONDecodeError as e:
                self.logger.error(f"ERROR al parsear JSON: {e}. Respuesta cruda: '{respuesta.text}'")
                return {"accion": "finalizar", "params": {"razon": "Error de parseo en la respuesta del modelo."}}
            except Exception as e:
                self.logger.error(f"ERROR al llamar al modelo de IA: {e}", exc_info=True)
                return {"accion": "finalizar", "params": {"razon": "Error en el módulo de decisión"}}

    # --- MÉTODOS DE APRENDIZAJE (Sin cambios) ---
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
```

---
path: analizar_imagen.py
---
```py
from PIL import Image
from vision import Vision
from logger_config import setup_logging
import logging

if __name__ == '__main__':
    setup_logging()
    main_logger = logging.getLogger("InteractIA")
    main_logger.info("--- Analizando imagen con el módulo de visión ---")

    vision = Vision()
    try:
        imagen = Image.open("prueba_vision_ocr.png")
        main_logger.info("Imagen cargada exitosamente.")
        
        datos_texto = vision.leer_texto_en_pantalla(imagen)
        
        if datos_texto:
            main_logger.info("Se ha detectado el siguiente texto en la imagen:")
            for bloque in datos_texto:
                print(bloque)
        else:
            main_logger.warning("No se detectó texto en la imagen o Tesseract no está configurado correctamente.")

    except FileNotFoundError:
        main_logger.error("No se encontró el archivo 'prueba_vision_ocr.png'.")
    except Exception as e:
        main_logger.error(f"Ocurrió un error: {e}")

    main_logger.info("--- Análisis de imagen finalizado ---")

```

---
path: aprendiz_gemini.py
---
```py
import time
from knowledge_base import KnowledgeBase
from controlador import Controlador

class AprendizGemini:
    """
    Habilidad para aprender tareas paso a paso consultando Gemini y almacenando el conocimiento adquirido.
    """
    def __init__(self):
        self.kb = KnowledgeBase()
        self.controlador = Controlador()
        self.historial = []
        self.url_gemini = "https://gemini.google.com/"

    def abrir_gemini(self):
        """Abre el navegador en la web de Gemini."""
        self.controlador.abrir_aplicacion("chrome.exe")
        time.sleep(2)
        self.controlador.escribir(self.url_gemini)
        self.controlador.presionar_tecla("enter")
        time.sleep(5)

    def generar_prompt(self, tarea):
        return (
            f"Indica paso a paso, y solo un paso a la vez, cómo realizar la siguiente tarea: {tarea}. "
            "No inventes nada. Espera a que te confirme o te proporcione información antes de dar el siguiente paso. "
            "Si necesitas información adicional, pídela de forma concreta."
        )

    def guardar_pasos(self, tarea, pasos):
        """Guarda la secuencia de pasos aprendidos en la base de conocimientos."""
        self.kb.guardar_habilidad(
            nombre_recurso=f"gemini_{tarea.replace(' ', '_').lower()}",
            tipo_recurso="Aprendizaje Gemini",
            datos_habilidad={
                "tarea": tarea,
                "pasos": pasos,
                "fuente": self.url_gemini
            }
        )

    def aprender_tarea(self, tarea):
        """
        Flujo principal: abre Gemini, formula el prompt, y guía la interacción paso a paso.
        El usuario debe interactuar manualmente con Gemini y copiar los pasos aquí para almacenarlos.
        """
        print(f"Abriendo Gemini para aprender la tarea: {tarea}")
        self.abrir_gemini()
        prompt = self.generar_prompt(tarea)
        print(f"Prompt para Gemini:\n{prompt}\n")
        print("Copia y pega aquí cada paso que Gemini te indique. Escribe 'fin' para terminar.")
        pasos = []
        while True:
            paso = input("Paso de Gemini: ")
            if paso.strip().lower() == "fin":
                break
            pasos.append(paso)
        self.guardar_pasos(tarea, pasos)
        print(f"Tarea '{tarea}' aprendida y almacenada.")

    def aprender_desinstalar_ultravnc(self):
        """
        Método para aprender cómo desinstalar UltraVNC utilizando Gemini.
        """
        tarea = "Desinstalar la aplicación UltraVNC en un ordenador con Windows"
        prompt = self.generar_prompt(tarea)
        print(f"Prompt para Gemini:\n{prompt}\n")
        print("Copia y pega aquí cada paso que Gemini te indique. Escribe 'fin' para terminar.")
        pasos = []
        while True:
            paso = input("Paso de Gemini: ")
            if paso.strip().lower() == "fin":
                break
            pasos.append(paso)
        self.guardar_pasos(tarea, pasos)
        print(f"Tarea '{tarea}' aprendida y almacenada.")

if __name__ == "__main__":
    ag = AprendizGemini()
    tarea = input("¿Qué tarea quieres aprender paso a paso con Gemini?: ")
    ag.aprender_tarea(tarea)

```

---
path: automatizar_notepad.py
---
```py
import pyautogui
import time
import subprocess

# Desactivamos el fail-safe para la ejecucin desatendida
pyautogui.FAILSAFE = False

def automatizar_notepad():
    """
    Abre el Bloc de notas, escribe un mensaje y toma una captura de pantalla.
    """
    try:
        print("Iniciando en 5 segundos...")
        time.sleep(5)

        # 1. Abrir el Bloc de notas
        print("Abriendo el Bloc de notas...")
        subprocess.Popen(['notepad.exe'])

        # Esperar a que la ventana del Bloc de notas aparezca y est activa
        time.sleep(2)

        # 2. Escribir en el Bloc de notas
        mensaje = "Hola, mundo! El agente de IA est funcionando."
        print(f"Escribiendo el mensaje: '{mensaje}'")
        pyautogui.write(mensaje, interval=0.05) # El intervalo hace que la escritura sea ms natural

        # Esperar un segundo
        time.sleep(1)

        # 3. Tomar la captura de pantalla como prueba
        nombre_archivo = "prueba_notepad.png"
        print(f"Tomando captura de pantalla y guardando como '{nombre_archivo}'.")
        pyautogui.screenshot(nombre_archivo)

        print("¡Automatización de Notepad completada!")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    automatizar_notepad()

```

---
path: buscar_tesseract.py
---
```py
import subprocess

def buscar_tesseract():
    """
    Busca el ejecutable de Tesseract en las rutas de instalación más comunes.
    Devuelve la ruta completa si lo encuentra, de lo contrario None.
    """
    print("Buscando Tesseract OCR...")
    comandos = [
        'dir "C:\Program Files\Tesseract-OCR\tesseract.exe" /s /b',
        'dir "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" /s /b'
    ]

    for cmd in comandos:
        try:
            print(f"Ejecutando: {cmd}")
            resultado = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
            if resultado and resultado.endswith("tesseract.exe"):
                print(f"(+) Tesseract encontrado en: {resultado}")
                return resultado
        except subprocess.CalledProcessError:
            # El comando falla si no encuentra el archivo, lo cual es esperado.
            continue
        except Exception as e:
            print(f"(-) Ocurrió un error inesperado al ejecutar el comando: {e}")
            continue
            
    print("(-) Tesseract no se encontró en las rutas de instalación comunes.")
    return None

if __name__ == '__main__':
    ruta_tesseract = buscar_tesseract()
    if ruta_tesseract:
        print(f"\nLa ruta del ejecutable de Tesseract es: {ruta_tesseract}")
    else:
        print("\nNo se pudo encontrar Tesseract. Por favor, asegúrate de que esté instalado.")

```

---
path: comunicador.py
---
```py
class Comunicador:
    def __init__(self, callback_hablar=None, callback_finalizar=None, callback_log=None):
        self.callback_hablar = callback_hablar
        self.callback_finalizar = callback_finalizar
        self.callback_log = callback_log

    def hablar(self, mensaje):
        if self.callback_hablar:
            self.callback_hablar(mensaje)
        else:
            print(f"Agente: {mensaje}")

    def finalizar_habla(self):
        if self.callback_finalizar:
            self.callback_finalizar()

    def log(self, mensaje):
        if self.callback_log:
            self.callback_log(mensaje)
```

---
path: config.py
---
```py
import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Credenciales y Endpoints ---

# Clave de API para el servicio de Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# URI de conexión para la base de datos MongoDB
MONGO_URI = os.getenv("MONGO_URI")

# --- Configuración de la Base de Datos ---

# Nombre de la base de datos principal
MONGODB_DATABASE_NAME = "interactia_db"

# Nombre de la colección para el historial de chat
MONGODB_CHAT_COLLECTION = "chat_history"

# Nombre de la colección para las oportunidades de aprendizaje descubiertas
MONGODB_OPORTUNIDADES_COLLECTION = "oportunidades_aprendizaje"

# Nombre de la colección para registrar sesiones de chat ya analizadas
MONGODB_SESIONES_ANALIZADAS_COLLECTION = "sesiones_analizadas"

# Número de mensajes a recuperar del historial de chat
CHAT_HISTORY_LENGTH = 20

# --- Configuraciones del Agente ---

# Modelo de Gemini a utilizar para la toma de decisiones
# Es importante elegir uno que sea multimodal (acepte imágenes y texto)
GEMINI_MODEL_NAME = "models/gemini-2.5-flash"

# --- Verificación de configuración ---

def verificar_configuracion():
    """
    Comprueba que las variables de entorno esenciales estén cargadas.
    """
    print("Verificando la configuración de la aplicación...")
    
    if not GEMINI_API_KEY or "SU_API_KEY" in GEMINI_API_KEY:
        print("(-) ADVERTENCIA: La variable de entorno GEMINI_API_KEY no está configurada.")
        return False
    else:
        print("(+) La API Key de Gemini está cargada.")

    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("(-) ADVERTENCIA: La variable de entorno MONGO_URI no está configurada.")
        return False
    else:
        print("(+) La URI de MongoDB está cargada.")
    
    print("\nConfiguración cargada correctamente.")
    return True

if __name__ == "__main__":
    verificar_configuracion()

```

---
path: contexto_manager.py
---
```py
import pyautogui
import logging

logger = logging.getLogger(__name__)

# Mapeo de partes de títulos de ventana a nombres de contexto normalizados
# La clave es una subcadena (en minúsculas) que se busca en el título de la ventana
# El valor es el nombre del contexto que se devolverá
MAPEO_CONTEXTO = {
    "bloc de notas": "Bloc de notas",
    "notepad": "Bloc de notas",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "visual studio code": "Visual Studio Code",
    "explorador de archivos": "Explorador de archivos",
    "file explorer": "Explorador de archivos",
    "símbolo del sistema": "Símbolo del sistema",
    "command prompt": "Command Prompt",
}

def detectar_contexto_actual() -> str:
    """
    Identifica la aplicación actualmente en primer plano analizando el título de la ventana activa.

    Returns:
        str: El nombre del contexto de la aplicación (ej. "Microsoft Word"), 
             o "General" si no se reconoce una aplicación específica.
    """
    try:
        ventana_activa = pyautogui.getActiveWindow()
        if not ventana_activa:
            logger.warning("No se pudo obtener la ventana activa. Devolviendo contexto 'General'.")
            return "General"

        titulo_ventana = ventana_activa.title.lower()
        logger.debug(f"Ventana activa detectada: '{titulo_ventana}'")

        # Buscar en el mapeo una coincidencia
        for clave, contexto in MAPEO_CONTEXTO.items():
            if clave in titulo_ventana:
                logger.info(f"Contexto reconocido: '{contexto}' a partir del título de la ventana.")
                return contexto
        
        # Si no hay ninguna coincidencia en el mapeo, es un contexto no específico
        logger.info(f"No se reconoció un contexto específico para '{titulo_ventana}'. Devolviendo 'General'.")
        return "General"

    except Exception as e:
        logger.error(f"Error al detectar el contexto de la ventana: {e}", exc_info=True)
        return "General"

if __name__ == '__main__':
    # Prueba para verificar la detección de contexto
    from logger_config import setup_logging
    setup_logging(log_level=logging.INFO)

    print("Detectando el contexto de la ventana actual en 3 segundos...")
    pyautogui.sleep(3)
    contexto = detectar_contexto_actual()
    print(f"--> Contexto detectado: {contexto}")
```

---
path: controlador.py
---
```py
import pyautogui
import time
import os
import logging

class Controlador:
    """
    Clase que abstrae el control del ratón, teclado y pantalla a través de pyautogui.
    """
    def __init__(self):
        """
        Inicializa el controlador y desactiva el fail-safe de pyautogui.
        """
        self.logger = logging.getLogger("InteractIA")
        pyautogui.FAILSAFE = False
        self.logger.debug("Controlador inicializado.")

    def enfocar_ventana(self, titulo: str) -> bool:
        """Encuentra una ventana por su título y la activa (la trae al frente)."""
        try:
            ventanas = pyautogui.getWindowsWithTitle(titulo)
            if ventanas:
                ventana = ventanas[0]
                ventana.activate()
                self.logger.info(f"Ventana '{titulo}' enfocada correctamente.")
                return True
            else:
                self.logger.warning(f"No se encontró ninguna ventana con el título: '{titulo}'")
                return False
        except Exception as e:
            self.logger.error(f"Error al enfocar la ventana '{titulo}': {e}")
            return False

    def mover_raton(self, x, y, duracion=1):
        self.logger.info(f"Moviendo ratón a ({x}, {y}).", extra={'extra_data': {'x': x, 'y': y, 'duracion': duracion}})
        pyautogui.moveTo(x, y, duration=duracion)

    def obtener_posicion_raton(self):
        pos = pyautogui.position()
        self.logger.debug(f"Posición del ratón obtenida: {pos}")
        return pos

    def escribir(self, texto, intervalo=0.05):
        # No loguear el texto completo por si es información sensible
        self.logger.info("Escribiendo texto.", extra={'extra_data': {'longitud': len(texto), 'intervalo': intervalo}})
        pyautogui.write(texto, interval=intervalo)

    def capturar_pantalla(self, nombre_archivo="captura_pantalla.png"):
        self.logger.info(f"Capturando pantalla y guardando como '{nombre_archivo}'.", extra={'extra_data': {'archivo': nombre_archivo}})
        pyautogui.screenshot(nombre_archivo)
        return nombre_archivo

    def esperar(self, segundos):
        self.logger.info(f"Esperando {segundos} segundos.", extra={'extra_data': {'segundos': segundos}})
        time.sleep(segundos)

    def clic(self, x=None, y=None, boton='left'):
        self.logger.info(f"Haciendo clic con botón {boton}.", extra={'extra_data': {'x': x, 'y': y, 'boton': boton}})
        pyautogui.click(x, y, button=boton)

    def presionar_tecla(self, tecla):
        self.logger.info(f"Presionando tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        if '+' in tecla:
            partes = tecla.split('+')
            pyautogui.hotkey(*partes)
        else:
            pyautogui.press(tecla)

    def mantener_tecla(self, tecla):
        self.logger.info(f"Manteniendo pulsada la tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        pyautogui.keyDown(tecla)

    def soltar_tecla(self, tecla):
        self.logger.info(f"Soltando la tecla: '{tecla}'.", extra={'extra_data': {'tecla': tecla}})
        pyautogui.keyUp(tecla)

    def scroll(self, direccion, clics):
        self.logger.info(f"Haciendo scroll hacia {direccion} ({clics} clics).", extra={'extra_data': {'direccion': direccion, 'clics': clics}})
        # pyautogui.scroll() toma un valor positivo para 'arriba' y negativo para 'abajo'
        if direccion == 'arriba':
            pyautogui.scroll(clics)
        elif direccion == 'abajo':
            pyautogui.scroll(-clics)

    def arrastrar_barra(self, direccion, porcentaje):
        self.logger.info(f"Arrastrando barra de scroll hacia {direccion} un {porcentaje}%.")
        
        # Obtener el tamaño de la ventana activa
        ventana = pyautogui.getActiveWindow()
        if not ventana:
            self.logger.warning("No se pudo obtener la ventana activa para arrastrar la barra.")
            return

        # Asumir que la barra de scroll vertical está a la derecha
        # y la horizontal abajo.
        if direccion == "vertical":
            # Punto de inicio del arrastre (borde derecho, a un 25% de la altura para empezar)
            x_inicio = ventana.left + ventana.width - 15 # Un poco a la izquierda del borde
            y_inicio = ventana.top + ventana.height * 0.25
            
            # Punto final del arrastre
            x_fin = x_inicio
            # La distancia a mover es un porcentaje de la altura total de la ventana
            distancia = ventana.height * (porcentaje / 100)
            y_fin = y_inicio + distancia

            # Realizar el arrastre
            pyautogui.moveTo(x_inicio, y_inicio)
            pyautogui.dragTo(x_fin, y_fin, duration=1.0, button='left')

        elif direccion == "horizontal":
            # Punto de inicio del arrastre (borde inferior, a un 25% del ancho)
            x_inicio = ventana.left + ventana.width * 0.25
            y_inicio = ventana.top + ventana.height - 15 # Un poco arriba del borde
            
            # Punto final del arrastre
            distancia = ventana.width * (porcentaje / 100)
            x_fin = x_inicio + distancia
            y_fin = y_inicio

            # Realizar el arrastre
            pyautogui.moveTo(x_inicio, y_inicio)
            pyautogui.dragTo(x_fin, y_fin, duration=1.0, button='left')
        
        self.logger.info("Arrastre de barra de scroll completado.")

if __name__ == '__main__':
    # Para probar este módulo de forma aislada, necesitamos configurar el logger
    from logger_config import setup_logging
    setup_logging()
    main_logger = logging.getLogger("InteractIA")

    main_logger.info("--- Iniciando prueba del Controlador --- ")
    controlador = Controlador()

    # controlador.abrir_aplicacion('notepad.exe') # This is now deprecated
    controlador.esperar(2)
    controlador.escribir("Prueba de logging en el controlador.")
    controlador.esperar(1)
    controlador.mover_raton(300, 300)
    controlador.capturar_pantalla("prueba_controlador_log.png")

    main_logger.info("--- Prueba del Controlador finalizada --- ")

```

---
path: db_inspector.py
---
```py
import os
import pymongo
from dotenv import load_dotenv
import json

# Función para convertir ObjectId a string
def default_converter(o):
    if isinstance(o, pymongo.mongo_client.ObjectId):
        return str(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
COLLECTION_TO_INSPECT = "habilidades"

# --- Script ---
if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
    print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
else:
    try:
        print(f"Conectando a MongoDB...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        print("Conexión exitosa.")

        print(f"Inspeccionando la colección '{COLLECTION_TO_INSPECT}' en la base de datos '{MONGODB_DATABASE_NAME}'...")
        
        collection = db[COLLECTION_TO_INSPECT]
        documentos = list(collection.find())
        
        if not documentos:
            print(f"No se encontraron documentos en la colección '{COLLECTION_TO_INSPECT}'.")
        else:
            print(f"\n--- Contenido de la Colección: {COLLECTION_TO_INSPECT} ---")
            for doc in documentos:
                # Usamos json.dumps para una impresión bonita y manejo de tipos de datos de Mongo
                print(json.dumps(doc, indent=4, default=str))
                print("---")
            print(f"--- Fin del Contenido ({len(documentos)} documentos) ---")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
```

---
path: get_chat_history.py
---
```py
import os
import pymongo
from dotenv import load_dotenv
import datetime
import argparse

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
MONGODB_CHAT_COLLECTION = "chat_history"

# --- Argumentos de línea de comandos ---
parser = argparse.ArgumentParser(description="Obtener el historial de chat de una sesión de InteractIA desde MongoDB.")
parser.add_argument("--session_id", required=True, help="El ID de la sesión para la cual obtener el historial.")
args = parser.parse_args()
SESSION_KEY = args.session_id

# --- Script ---
if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
    print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
    print("Por favor, asegúrate de que MONGO_URI esté definida en tu entorno o en un archivo .env.")
else:
    try:
        print(f"Conectando a MongoDB con la URI proporcionada...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]
        print("Conexión exitosa.")

        print(f"Buscando historial de chat para la sesión: {SESSION_KEY}...")
        mensajes_cursor = collection_chats.find(
            {"session_key": SESSION_KEY}
        ).sort("timestamp", pymongo.ASCENDING)

        historial = list(mensajes_cursor)

        if not historial:
            print(f"No se encontró historial de chat para la sesión '{SESSION_KEY}'.")
        else:
            print(f"--- Historial de Chat para la sesión: {SESSION_KEY} ---")
            for msg in historial:
                role = msg.get('role', 'desconocido')
                content = msg.get('content', {}).get('texto', '(sin texto)')
                timestamp = msg.get('timestamp', 'sin fecha')
                if isinstance(timestamp, datetime.datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {role}: {content}")
            print(f"--- Fin del Historial ---")
            print(f"Se encontraron {len(historial)} mensajes.")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
        print("Verifica que la URI de conexión es correcta y que la base de datos está accesible.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
```

---
path: get_latest_session_info.py
---
```py
import os
import re
import pymongo
from dotenv import load_dotenv
import datetime
import argparse
import json

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ---
# Configuración
# ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
MONGODB_CHAT_COLLECTION = "chat_history"
LOG_FILE_PATH = "interactia_debug.log"

# ---
# Funciones
# ---

def get_latest_session_id_from_log(log_path):
    """Lee el archivo de log desde el final para encontrar el último ID de sesión."""
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Buscar el ID de sesión desde la última línea hacia atrás
        for line in reversed(lines):
            match = re.search(r'interactia-([a-zA-Z0-9]+)', line)
            if match:
                session_id = match.group(0)
                print(f"Último ID de sesión encontrado: {session_id}")
                return session_id
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de log en '{log_path}'")
    except Exception as e:
        print(f"Error al leer el archivo de log: {e}")
    return None

def get_chat_history(session_id):
    """Recupera y muestra el historial de chat para un ID de sesión dado."""
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
        return

    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]

        mensajes_cursor = collection_chats.find(
            {"session_key": session_id}
        ).sort("timestamp", pymongo.ASCENDING)

        historial = list(mensajes_cursor)

        if not historial:
            print(f"No se encontró historial de chat para la sesión '{session_id}'.")
        else:
            print(f"\n--- Historial de Chat para la sesión: {session_id} ---")
            for msg in historial:
                role = msg.get('role', 'desconocido')
                content = msg.get('content', {}).get('texto', '(sin texto)')
                timestamp = msg.get('timestamp', 'sin fecha')
                if isinstance(timestamp, datetime.datetime):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] {role}: {content}")
            print(f"--- Fin del Historial ---")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado al obtener el chat: {e}")

def get_session_logs(session_id, log_path):
    """Filtra y muestra los logs para un ID de sesión específico."""
    print(f"\n--- Logs para la sesión: {session_id} ---")
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if session_id in line:
                    try:
                        log_json = json.loads(line)
                        print(f"[{log_json.get('timestamp')}] [{log_json.get('level')}] [{log_json.get('module')}:{log_json.get('function')}:{log_json.get('line')}] {log_json.get('message')}")
                    except json.JSONDecodeError:
                        print(line.strip()) # Imprimir la línea si no es un JSON válido
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de log en '{log_path}'")
    except Exception as e:
        print(f"Error al leer los logs de la sesión: {e}")
    print(f"--- Fin de los Logs ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtener información de la última sesión de depuración de InteractIA.")
    parser.add_argument("--session_id", help="ID de sesión específico a buscar. Si no se provee, se busca el último en el log.")
    args = parser.parse_args()

    session_to_find = args.session_id
    
    if not session_to_find:
        session_to_find = get_latest_session_id_from_log(LOG_FILE_PATH)

    if session_to_find:
        get_chat_history(session_to_find)
        get_session_logs(session_to_find, LOG_FILE_PATH)
    else:
        print("No se pudo determinar un ID de sesión para continuar.")

```

---
path: interactia.md
---
```md
# InteractIA: Un Agente de IA Autónomo y Evolutivo

Este documento detalla la arquitectura, filosofía y mecanismos internos de InteractIA, un agente de IA diseñado para operar en un entorno de escritorio, aprender de la interacción con el usuario y ejecutar tareas de forma autónoma.

## 1. Filosofía y Principios Fundamentales

1.  **Emulación de Usuario Físico**: El agente no tiene "atajos". Su única forma de interactuar con el sistema es a través de la visión (captura de pantalla) y el control de periféricos (ratón y teclado), emulando a un usuario humano.

2.  **Cerebro vs. Cuerpo**: La arquitectura se divide conceptualmente:
    *   **Cerebro (`agente.py`):** Es el centro de razonamiento, planificación y aprendizaje. Orquesta el ciclo de operación, gestiona la memoria y se comunica con el modelo de IA (LLM).
    *   **Cuerpo (`controlador.py`, `vision.py`):** Son los sentidos y las extremidades. `vision.py` actúa como los ojos (capturando la pantalla y usando OCR) y `controlador.py` como las manos (ejecutando clics y pulsaciones de teclas).

3.  **Aprendizaje Continuo y Supervisado**: El agente no es una herramienta estática. Su propósito es aprender y mejorar a través de la interacción. El usuario actúa como un supervisor final, validando el conocimiento que el agente destila de sus experiencias.

## 2. Arquitectura del Agente

### El Ciclo de Ejecución Principal (Motor Autónomo)

El corazón del agente es su bucle de ejecución principal, implementado en el método `stream_run` de `agente.py`. A diferencia de un sistema de un solo paso, InteractIA opera en un ciclo continuo (`while True`) que le permite persistir en una tarea hasta completarla. Este bucle solo se detiene si:

*   La tarea se completa con éxito (`finalizar`).
*   El agente necesita la intervención del usuario (`pedir_aclaracion` o `proponer_aprendizaje`).
*   Ocurre un error irrecuperable.

### El Ciclo de Pensamiento (Observar-Consultar-Pensar-Actuar)

Dentro del bucle principal, en cada iteración, se ejecuta un ciclo de pensamiento mejorado:

1.  **Observar**: El agente captura el estado actual de la pantalla.
2.  **Consultar Memoria**: El agente invoca a su módulo de memoria activa (`memoria_chat_mongodb.py`) para obtener un resumen inteligente y conciso de la conversación hasta la fecha. Este resumen, y no el historial en bruto, se convierte en el contexto principal.
3.  **Pensar**: Usando el resumen de la memoria, su conocimiento previo (KB) y la captura de pantalla, el agente crea un plan y decide la siguiente acción atómica a realizar.
4.  **Actuar**: El agente ejecuta la acción decidida (ej. un clic, escribir texto) y el ciclo vuelve a empezar.

### 3.1. Memoria Activa y Relevante

La memoria de InteractIA ha evolucionado de un simple log persistente a una capa de inteligencia activa. En lugar de pasar el historial de chat en bruto al cerebro del agente, el sistema ahora pre-procesa la conversación para extraer relevancia.

*   **Procesador Activo (`memoria_chat_mongodb.py`):** El módulo de memoria ya no es un simple almacén. Ahora contiene lógica para invocar a un LLM y actuar como un "analista de memoria".
*   **Generación de Contexto:** Antes de cada ciclo de pensamiento, el agente le pide al módulo de memoria un resumen de la conversación. El módulo recupera el historial reciente y le pide al LLM que lo sintetice en los puntos clave: intención del usuario, entidades importantes, estado actual y preguntas pendientes.
*   **Contexto de Alta Calidad:** El resultado es un contexto conciso y de alta calidad (ej: *"El usuario quiere los datos de ventas del último trimestre del fichero 'ventas_Q3.xlsx'"*) que se inyecta directamente en el prompt principal del agente. Esto permite al agente tomar decisiones más rápidas y precisas.
*   **Consultas Específicas:** El sistema también permite al agente hacer preguntas concretas a su memoria para resolver ambigüedades (ej: *"¿Cuál fue el nombre del fichero que se mencionó antes?"*).

Este enfoque reduce drásticamente la carga cognitiva del agente principal y representa un paso clave hacia un razonamiento más eficiente y similar al humano.

### El Proceso de Planificación Proactiva

Cuando el agente se enfrenta a un objetivo para el que no tiene una habilidad predefinida, no se rinde. Su "cerebro" (`_construir_prompt`) está diseñado para instruir al modelo de IA a que actúe como un planificador. Se le presenta el objetivo, el contexto de la conversación y la lista de **habilidades fundamentales** que posee (cargadas desde la Knowledge Base). Con esta información, el LLM debe formular un plan y derivar la siguiente acción concreta para avanzar en él.

## 3. Gestión del Conocimiento: El Ciclo de Aprendizaje

InteractIA trasciende la simple ejecución gracias a su sofisticado ciclo de gestión del conocimiento.

### La Base de Conocimiento (KnowledgeBase)

Implementada en `knowledge_base.py` y respaldada por MongoDB, es la memoria a largo plazo del agente. Almacena "habilidades" en formato estructurado. Crucialmente, las propias capacidades fundamentales del agente se cargan desde un recurso especial en la KB (`habilidades_fundamentales_agente`), haciendo el sistema altamente modular.

### El Flujo: Ignorar -> Aprender -> Conocer

El vocabulario de la KB refleja un proceso de aprendizaje natural:

*   **Conocer (`conocer_habilidad`)**: El acto de consultar la KB para ver si existe una habilidad.
*   **Ignorar**: El estado en el que se encuentra el agente cuando `conocer_habilidad` no devuelve nada. Este estado activa el proceso de planificación o aprendizaje.
*   **Aprender (`aprender_habilidad`)**: El acto de consolidar y guardar un nuevo conocimiento en la KB.

### 3.2. El Ciclo de Aprendizaje Supervisado: Destilación y Meta-Aprendizaje

El aprendizaje es la característica que define a InteractIA. El agente puede aprender de dos formas: en tiempo real a partir de la conversación activa (Destilación Directa) y de forma proactiva analizando conversaciones pasadas (Meta-Aprendizaje).

#### Destilación Directa (en tiempo real)

Cuando el agente completa una tarea guiado por el usuario, puede usar la acción `proponer_aprendizaje`. Esto desencadena un proceso donde el agente resume la interacción actual en una habilidad estructurada y se la propone al usuario para guardarla en la Knowledge Base. Es un aprendizaje inmediato y contextual.

#### Meta-Aprendizaje Proactivo (sobre el historial)

Esta es la forma más avanzada de aprendizaje, donde el agente reflexiona sobre sus experiencias pasadas. El objetivo es descubrir múltiples habilidades que pudieron haberse enseñado en una sola conversación y procesarlas de forma individual y robusta.

**1. El Disparador**

Actualmente, este ciclo se inicia de forma manual. El usuario puede pedirle al agente que inicie el proceso con el comando `/aprender_de_historial`.

**2. Fase de Descubrimiento**

Una vez iniciado, el agente busca en su memoria una conversación que no haya analizado previamente. Su objetivo se convierte en: "Analiza este chat y extrae TODAS las posibles habilidades".
*   **Extracción de Hipótesis**: Usando al LLM, el agente identifica todas las "oportunidades de aprendizaje" de esa conversación.
*   **Cola de Oportunidades**: Cada oportunidad se guarda como un documento individual en una nueva base de datos (`oportunidades_aprendizaje`), con un estado inicial de `pendiente_verificacion`.
*   **Registro de Análisis**: La conversación original se marca como analizada para no volver a procesarla, usando la colección `sesiones_analizadas`.

**3. Fase de Procesamiento Individual**

En un ciclo posterior, el agente toma una única oportunidad de la cola que esté pendiente.
*   **Validación de Hipótesis**: El agente presenta la habilidad potencial al usuario para que confirme si es útil y merece ser formalizada (Ej: *"He encontrado una habilidad potencial de una conversación pasada: 'Cómo buscar un fichero por su extensión'. ¿Crees que es útil que intente aprenderla?"*).
*   **Actualización de Estado**: Si el usuario aprueba, el estado de la oportunidad cambia a `verificacion_exitosa`. Si la rechaza, a `rechazada_por_usuario`. De esta forma, aunque en un chat hubiera 3 habilidades y el usuario descarte una, las otras dos no se pierden y quedan pendientes en la cola.
*   **Destilación Final**: Las oportunidades que han sido verificadas con éxito pueden ser procesadas en un futuro para, usando el contexto de la conversación original, destilar los pasos exactos y proponer la habilidad final y estructurada a la Knowledge Base.

## 4. Características Notables

*   **Autonomía**: Gracias a su bucle principal, puede ejecutar tareas de múltiples pasos sin intervención.
*   **Memoria Conversacional Persistente**: El historial de la conversación no solo se incluye en el contexto de pensamiento, sino que se guarda de forma persistente en una base de datos MongoDB. Esto le permite recordar conversaciones entre reinicios. (Ver sección 3.1 para más detalles).
*   **Independencia de Resolución**: Utiliza coordenadas relativas para las acciones de clic, lo que lo hace robusto a diferentes resoluciones de pantalla.
*   **Capacidades Externalizadas**: Sus habilidades fundamentales no están codificadas, sino que se cargan desde la Base de Conocimiento, permitiendo una gran modularidad.
*   **Robustez**: Implementa un sistema de auto-corrección para respuestas JSON mal formadas del LLM y un sistema de depuración que genera un log detallado (`interactia_debug.log`).

## 5. Errores detectados

- hay ejecuciones que son exitosas pero el agente no detecta que se ha cumplido el objetivo.
- las combinaciones de teclas tipo win+e no funcionan pero sin embargo, solo la tecla win sí funciona.

## 6. Propuesta de Futuro: Modelo de Tutoría Jerárquica

### 1. Concepto Central

La idea es crear un sistema de dos niveles donde una instancia de InteractIA (el **Supervisor**) monitoriza, depura y guía a otra instancia (el **Controlado** o "trabajador"). La comunicación del Supervisor hacia el Controlado se limita a emular a un usuario humano, escribiendo instrucciones en su cuadro de chat. Sin embargo, el Supervisor tiene acceso privilegiado de "lectura" tanto a la memoria (historial de chat) como al "cerebro" (estado interno y logs) del Controlado, además de poder ver la pantalla completa.

Esto crea una dinámica de **Tutor-Aprendiz**, donde el Supervisor ayuda al Aprendiz a superar obstáculos, permitiendo resolver problemas más complejos y, a la vez, generando un historial de chat limpio y exitoso en el agente Controlado, ideal para el aprendizaje futuro.

### 2. Análisis de Pros y Contras

**Pros (Ventajas Estratégicas):**

*   **Depuración y Tutoría Avanzada:** Si un agente se atasca, el Supervisor puede analizar su estado interno (su "razonamiento"), ver qué está fallando y darle una instrucción correctiva. Es un mecanismo de auto-depuración y auto-mejora extremadamente potente.
*   **Descomposición de Tareas Complejas:** Permite abordar problemas de un nivel de abstracción superior. Un usuario podría darle al Supervisor un objetivo muy complejo (ej: "Prepara un informe de ventas trimestral"). El Supervisor lo descompondría en pasos simples que iría pasando uno a uno al agente Controlado.
*   **Generación de Datos de Entrenamiento de Alta Calidad:** Al guiar al agente Controlado por el camino correcto, el historial de chat resultante de esa instancia es un ejemplo "perfecto" de cómo completar una tarea, ideal para el ciclo de meta-aprendizaje.
*   **Alineación con la Filosofía del Agente:** Refuerza el principio de "no atajos". El Supervisor está forzado a actuar como un usuario, lo que mantiene la coherencia del sistema.

**Contras (Desafíos Técnicos y Conceptuales):**

*   **Comunicación Entre Instancias (IPC):** Es el mayor desafío. La solución propuesta es utilizar **MongoDB como un bus de estado**. El agente Controlado escribiría su estado actual (objetivo, última acción, error) en un documento dedicado, y el Supervisor lo leería para obtener telemetría en tiempo real.
*   **Consumo de Recursos:** Ejecutar dos instancias completas de InteractIA podría consumir una cantidad considerable de CPU y memoria.
*   **Definición del "Acceso al Cerebro":** Se necesitaría definir con precisión qué conjunto de datos del "cerebro" se exponen de forma segura y útil.
*   **Riesgo de Bucles:** El flujo de interacción debe ser cuidadosamente diseñado para evitar bucles infinitos.

### 3. Flujo de Trabajo Propuesto

1.  **Activación:** El usuario, en la ventana de `interactia_1234`, pulsa un nuevo botón "Crear Supervisor".
2.  **Lanzamiento:** El sistema ejecuta `python main.py --supervisando-a 1234`, abriendo una nueva ventana, `interactia_5678` (el Supervisor).
3.  **Asignación de Tarea:** El usuario le da un objetivo al Supervisor: "Asegúrate de que la instancia 1234 abre la terminal".
4.  **Observación (Supervisor):** Lee el documento de estado en MongoDB de `interactia_1234` y observa la pantalla.
5.  **Pensamiento (Supervisor):** Ve que `1234` está atascado o ha cometido un error.
6.  **Actuación (Supervisor):** Usa su `controlador` para encontrar el cuadro de texto de `1234` y escribe una instrucción correctiva.
7.  El ciclo se repite hasta que la tarea se completa.

## 7. Análisis del Sistema de Aprendizaje y Propuesta de Autonomía

### Situación Actual: Un Sistema Híbrido y Manual

Actualmente, el agente aprende de dos maneras principales, ambas requiriendo intervención manual:

1.  **Registro Directo (Los scripts `registrar_*.py`):**
    *   **Cómo funciona:** Creas un script de Python (como los que hemos visto) donde defines una "habilidad" en un diccionario y usas la función `kb.aprender_habilidad()` para guardarla en la base de datos.
    *   **Análisis:** Este método es robusto y bueno para definir habilidades complejas y fundamentales (como las de navegación o las acciones básicas). Sin embargo, es un proceso de desarrollo de software, no de aprendizaje autónomo. Cada nueva habilidad requiere que escribas y ejecutes código nuevo.

2.  **Aprendizaje Semi-Autónomo (El script `aprendiz_gemini.py`):**
    *   **Cómo funciona:** Este script abre la web de Gemini en Chrome y te pide que le preguntes a Gemini cómo hacer una tarea. Luego, **tú tienes que copiar y pegar manualmente** cada paso que te da Gemini en la terminal para que el script los guarde como una nueva habilidad.
    *   **Análisis:** Esta es una idea muy potente y un gran primer paso hacia la autonomía. El agente intenta usar una fuente de conocimiento externa (Gemini) para aprender. El punto débil es la dependencia del usuario para hacer de "puente" entre la web de Gemini y el script.

**En resumen: El sistema actual es funcional, pero no es autónomo. El agente no puede crear nuevas habilidades por sí mismo a partir de su experiencia o de consultas a Gemini sin una intervención manual significativa.**

### Propuesta para la Autonomía Total: Un Plan en 3 Fases

Para lograr que el agente aprenda de forma verdaderamente autónoma, te propongo el siguiente plan evolutivo:

#### Fase 1: Del Script a la Conversación (Auto-Registro de Habilidades)

*   **Objetivo:** Eliminar por completo la necesidad de los scripts `registrar_*.py` para habilidades sencillas.
*   **Cómo:** Potenciaremos la acción `proponer_aprendizaje` que el agente ya conoce.
    1.  Cuando el agente complete una tarea nueva o una secuencia de acciones que considere útil, podría usar `proponer_aprendizaje` para decirte: "He aprendido a hacer X. ¿Quieres que lo guarde como una nueva habilidad llamada 'habilidad_X'?".
    2.  Si le respondes "sí", el propio agente llamaría internamente a la función `kb.aprender_habilidad()` para guardar esa nueva secuencia de acciones en su base de conocimiento, sin necesidad de ningún script.

#### Fase 2: De la Web a la API (Automatización del Aprendizaje con Gemini)

*   **Objetivo:** Eliminar el paso manual de copiar y pegar en `aprendiz_gemini.py`.
*   **Cómo:** El agente ya usa la API de Gemini para "pensar". Podemos crear un "modo de aprendizaje" en el que use esa misma API para aprender.
    1.  Cuando se enfrente a una tarea que no sabe cómo resolver, el agente podría entrar en "modo aprendizaje".
    2.  En este modo, en lugar de preguntarse a sí mismo qué hacer, le preguntaría a la API de Gemini (con un prompt similar al de `aprendiz_gemini.py`): "¿Cómo puedo 'desinstalar UltraVNC'? Dame los pasos".
    3.  El agente recibiría la respuesta directamente, la analizaría, y guardaría los pasos como una nueva habilidad. **Cero intervención del usuario.**

#### Fase 3: Del Aprendizaje Reactivo al Proactivo (Iniciativa Propia)

*   **Objetivo:** Que el agente decida por sí mismo cuándo y qué necesita aprender.
*   **Cómo:** Una vez completadas las fases 1 y 2, el agente tendría las herramientas para aprender por sí solo. El siguiente paso es darle la iniciativa.
    1.  **Auto-mejora por fallo:** Si el agente falla repetidamente en una tarea, podría activar automáticamente el "modo aprendizaje" (Fase 2) para buscar una solución.
    2.  **Optimización de secuencias:** El agente podría analizar su propio historial de acciones y detectar patrones. Si ve que para hacer "Y" siempre ejecuta los pasos A, B y C, podría proponerte: "He notado que siempre hago A, B y C juntos. ¿Quieres que cree una nueva habilidad 'Y' que haga estos tres pasos de una vez?".
```

---
path: interactia_gui.py
---
```py
import tkinter as tk
from tkinter import ttk
from agente import Agente
import threading
import subprocess
import sys

class InteractIAGUI:
    def __init__(self, root, titulo="InteractIA - Agente Inteligente", id_objetivo=None):
        self.root = root
        self.titulo_ventana = titulo
        self.root.title(self.titulo_ventana)
        self.root.geometry("800x600")

        # --- Layout Principal ---
        self.main_frame = ttk.Frame(self.root, padding="0")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Placeholder para el Sidebar (Fase 3)
        # self.sidebar_frame = ttk.Frame(self.main_frame, width=200, relief=tk.RIDGE)
        # self.sidebar_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W))

        # --- Frame Principal del Chat ---
        self.chat_area_frame = ttk.Frame(self.main_frame, padding="10")
        self.chat_area_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # --- Historial de Chat Unificado ---
        self.chat_history_text = tk.Text(self.chat_area_frame, wrap="word", state='disabled', font=('Arial', 10))
        self.chat_history_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.chat_area_frame.rowconfigure(0, weight=1)
        self.chat_area_frame.columnconfigure(0, weight=1)

        # Scrollbar para el chat
        self.scrollbar = ttk.Scrollbar(self.chat_area_frame, orient=tk.VERTICAL, command=self.chat_history_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.chat_history_text['yscrollcommand'] = self.scrollbar.set

        # --- Indicador de Carga ---
        self.loading_bar = ttk.Progressbar(self.chat_area_frame, mode='indeterminate')
        self.loading_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.loading_bar.grid_remove() # Oculto por defecto

        # --- Frame de Entrada de Comandos ---
        self.input_frame = ttk.Frame(self.chat_area_frame)
        self.input_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        self.input_frame.columnconfigure(1, weight=1)

        # Botón para adjuntar archivos (Fase 3)
        self.upload_button = ttk.Button(self.input_frame, text="+", width=3)
        self.upload_button.grid(row=0, column=0, padx=(0, 5))

        self.input_entry = ttk.Entry(self.input_frame)
        self.input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.input_entry.bind("<Return>", self.process_command)

        self.send_button = ttk.Button(self.input_frame, text="Enviar", command=self.process_command)
        self.send_button.grid(row=0, column=2, padx=5)

        # --- Botón para Instancia Supervisora ---
        if not id_objetivo: # Solo mostrar si no es una instancia ya supervisada
            self.supervisor_button = ttk.Button(self.input_frame, text="Crear Supervisor", command=self.crear_instancia_supervisora)
            self.supervisor_button.grid(row=0, column=3, padx=5)

        # --- Inicialización ---
        self._configure_chat_tags()
        self.agente = Agente(
            id_ventana=self.titulo_ventana,
            id_objetivo=id_objetivo,
            callback_hablar=self.mostrar_mensaje_agente,
            callback_finalizar=self.finalizar_respuesta_agente,
            callback_log=self.insert_log_message
        )
        self._agent_writing = False

    def crear_instancia_supervisora(self):
        """Lanza una nueva instancia en modo Supervisor para ayudar a esta instancia."""
        try:
            # Extraer el ID de la ventana actual. El formato es "interactia-XXXXXX"
            current_id = self.titulo_ventana.split('-')[-1]
            
            # Usar sys.executable para asegurar que se usa el mismo intérprete de Python
            comando = [
                sys.executable, 
                'main.py', 
                '--supervisando-a', 
                current_id
            ]
            
            # Usar Popen para lanzar el proceso de forma no bloqueante
            subprocess.Popen(comando)
            self.insert_message(f"Lanzando nueva instancia supervisora para esta ventana (ID: {current_id})", 'agent')
        except Exception as e:
            self.insert_message(f"Error al lanzar instancia supervisora: {e}", 'agent')

    def _configure_chat_tags(self):
        """Configura los tags para roles y formatos."""
        self.chat_history_text.tag_configure('user', justify='right', background='#E0F7FA', relief='raised', borderwidth=1, lmargin1=60, lmargin2=60, spacing3=5)
        self.chat_history_text.tag_configure('agent', justify='left', background='#F0F0F0', foreground='black', relief='raised', borderwidth=1, lmargin1=10, lmargin2=10, spacing3=5)
        self.chat_history_text.tag_configure('log', foreground='gray', font=('Arial', 8))

    def insert_message(self, message, role):
        """Inserta un mensaje completo en el historial de chat."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"[{timestamp}] {message}\n\n", role)
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def insert_log_message(self, message):
        """Inserta un mensaje de log en el historial de chat."""
        self.root.after(0, self._insert_log_message, message)

    def _insert_log_message(self, message):
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"{message}\n", 'log')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def process_command(self, event=None):
        """Procesa el comando del usuario, lo muestra y arranca el agente."""
        command = self.input_entry.get()
        if not command:
            return

        self.insert_message(command, 'user')
        self.input_entry.delete(0, tk.END)

        self.loading_bar.grid()
        self.loading_bar.start(10)

        self.agente.establecer_objetivo(command)
        thread = threading.Thread(target=self.agente.stream_run)
        thread.start()

    def mostrar_mensaje_agente(self, token):
        """Callback thread-safe para insertar un token de la respuesta del agente."""
        self.root.after(0, self._insert_agent_token, token)

    def finalizar_respuesta_agente(self):
        """Callback thread-safe para señalar el fin de la respuesta."""
        self.root.after(0, self._finalize_agent_response)

    def _insert_agent_token(self, token):
        """Inserta un token en la GUI, iniciando un nuevo bloque de agente si es necesario."""
        from datetime import datetime
        self.chat_history_text.config(state='normal')
        
        if not self._agent_writing:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.chat_history_text.insert(tk.END, f"Agente [{timestamp}]: ", 'agent')
            self._agent_writing = True
            # Detener la barra de progreso al recibir el primer token
            self.loading_bar.stop()
            self.loading_bar.grid_remove()

        self.chat_history_text.insert(tk.END, token, 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

    def _finalize_agent_response(self):
        """Finaliza el bloque de respuesta del agente."""
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, "\n\n", 'agent')
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)
        self._agent_writing = False
        # Aquí se llamaría al parser de Markdown en el futuro (Fase 2)
        # self._apply_markdown_formatting()

if __name__ == "__main__":
    root = tk.Tk()
    app = InteractIAGUI(root)
    root.mainloop()
```

---
path: interactia_sube_compila.py
---
```py
import subprocess
import datetime
import sys

def run_and_log(command_str):
    """Ejecuta un comando como una cadena y muestra su salida en tiempo real."""
    print(f"--- Ejecutando: {command_str} ---")
    try:
        process = subprocess.Popen(command_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
        
        process.wait()
        output = "".join(output_lines)

        if process.returncode != 0:
            if "nothing to commit" in output or "nada para hacer commit" in output:
                 print("--- INFO: No habia nuevos cambios para incluir en el commit. ---")
                 return True
            
            print(f"!!! ERROR: El comando finalizo con codigo de salida {process.returncode} !!!")
            return False
            
        print("--- Comando finalizado con exito ---")
        return True

    except Exception as e:
        print(f"!!! Ocurrio un error inesperado al ejecutar el comando: {e} !!!")
        return False

def main():
    """
    Script para automatizar el proceso de commit y compilacion de la aplicacion InteractIA.
    """
    print(">>> INICIANDO SCRIPT DE COMMIT Y COMPILACION AUTOMATICA <<<")

    if not run_and_log("git add ."):
        print(">>> Proceso abortado por error en 'git add'.")
        sys.exit(1)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Build automatico: {timestamp}"
    if not run_and_log(f'git commit -m "{commit_message}"'):
        print("ADVERTENCIA: 'git commit' no se completo como se esperaba, pero se continua con la compilacion.")
    
    # --- COMANDO CORREGIDO ---
    # Se anade la ruta absoluta al proyecto para que PyInstaller la use.
    pyinstaller_command = (
        "pyinstaller --onefile --noconsole --name InteractIA "
        "--paths e:\\OneDrive\\MiCodigo\\VS\\InteractIA "
        "--hidden-import=agente "
        "--hidden-import=controlador "
        "--hidden-import=vision "
        "--hidden-import=knowledge_base "
        "--hidden-import=memoria_chat_mongodb "
        "--hidden-import=logger_config "
        "--hidden-import=comunicador "
        "--hidden-import=contexto_manager "
        "--hidden-import=config "
        "--hidden-import=lock_manager "
        "main.py"
    )
    
    if not run_and_log(pyinstaller_command):
        print(">>> Proceso abortado por error en la compilacion con PyInstaller.")
        sys.exit(1)

    print(">>> SCRIPT FINALIZADO. La aplicacion ha sido compilada en la carpeta 'dist'. <<<")

if __name__ == "__main__":
    main()
```

---
path: knowledge_base.py
---
```py
import pymongo
from config import MONGO_URI
import datetime
from datetime import timezone

class KnowledgeBase:
    """
    Gestiona la interacción con la base de datos de conocimiento en MongoDB.
    """
    def __init__(self, db_name="interactia_db", collection_name="habilidades"):
        """
        Inicializa la conexión a la base de datos y la colección.
        """
        self.client = None
        self.db = None
        self.collection = None
        try:
            if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
                raise ValueError("La URI de MongoDB no está configurada correctamente en el archivo .env")
            
            self.client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Forzar la conexión para verificar que es válida
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            print(f"(+) Conectado a MongoDB. Base de datos: '{db_name}', Colección: '{collection_name}'.")

        except (pymongo.errors.ConnectionFailure, pymongo.errors.ConfigurationError, ValueError) as e:
            print(f"(-) ERROR al inicializar KnowledgeBase: {e}")
            self.client = None # Asegurarse de que no se use un cliente inválido

    def aprender_habilidad(self, nombre_recurso, tipo_recurso, datos_habilidad):
        """
        Guarda o actualiza una habilidad en la base de datos.

        Args:
            nombre_recurso (str): El nombre único del recurso (ej. 'api.escriva.org').
            tipo_recurso (str): El tipo de recurso (ej. 'API', 'Sitio Web').
            datos_habilidad (dict): El diccionario con los datos estructurados de la habilidad.
        """
        if not self.client:
            print("(-) No se puede guardar la habilidad, no hay conexión con la base de datos.")
            return None

        documento = {
            "nombre_recurso": nombre_recurso,
            "tipo_recurso": tipo_recurso,
            "datos": datos_habilidad,
            "fecha_actualizacion": datetime.datetime.now(timezone.utc)
        }
        
        # Actualiza si existe, inserta si es nuevo (upsert)
        resultado = self.collection.update_one(
            {"nombre_recurso": nombre_recurso},
            {"$set": documento},
            upsert=True
        )
        
        if resultado.upserted_id:
            print(f"(+) Habilidad '{nombre_recurso}' guardada exitosamente (nuevo documento).")
            return resultado.upserted_id
        elif resultado.modified_count > 0:
            print(f"(+) Habilidad '{nombre_recurso}' actualizada exitosamente.")
            return self.collection.find_one({"nombre_recurso": nombre_recurso})["_id"]
        else:
            print(f"(+) La habilidad '{nombre_recurso}' ya estaba actualizada.")
            return self.collection.find_one({"nombre_recurso": nombre_recurso})["_id"]

    def conocer_habilidad(self, nombre_recurso):
        """
        Busca y devuelve una habilidad por su nombre.

        Args:
            nombre_recurso (str): El nombre del recurso a buscar.

        Returns:
            dict: El documento de la habilidad si se encuentra, de lo contrario None.
        """
        if not self.client:
            print("(-) No se puede consultar la habilidad, no hay conexión con la base de datos.")
            return None
            
        return self.collection.find_one({"nombre_recurso": nombre_recurso})

    def conocer_habilidad_por_accion(self, nombre_accion: str):
        """
        Busca un documento de habilidad que contenga una acción específica por su nombre.

        Args:
            nombre_accion (str): El nombre de la acción a buscar dentro de la habilidad.

        Returns:
            dict: El documento de la habilidad si se encuentra, de lo contrario None.
        """
        if not self.client:
            print("(-) No se puede consultar la habilidad, no hay conexión con la base de datos.")
            return None
        
        query = {
            "datos.acciones.nombre": nombre_accion
        }
        return self.collection.find_one(query)

    def conocer_habilidades_por_contexto(self, contextos: list):
        """
        Busca y devuelve todas las habilidades que coinciden con una lista de contextos.

        Args:
            contextos (list[str]): Una lista de contextos a buscar (ej. ["Microsoft Word", "General"]).

        Returns:
            list: Una lista de documentos de habilidad que coinciden.
        """
        if not self.client:
            print("(-) No se puede consultar habilidades, no hay conexión con la base de datos.")
            return []
        
        query = {
            "datos.contexto_aplicacion": {
                "$in": contextos
            }
        }
        return list(self.collection.find(query))

    def get_all_skills(self):
        """
        Devuelve todas las habilidades de la base de datos.

        Returns:
            list: Una lista de todas las habilidades.
        """
        if not self.client:
            print("(-) No se puede consultar las habilidades, no hay conexión con la base de datos.")
            return []
            
        return list(self.collection.find({}, {'_id': 0}))

    def olvidar_habilidad(self, nombre_recurso):
        """Elimina una habilidad de la base de datos por su nombre."""
        if not self.client:
            print("(-) No se puede olvidar la habilidad, no hay conexión con la base de datos.")
            return None
        
        resultado = self.collection.delete_one({"nombre_recurso": nombre_recurso})
        if resultado.deleted_count > 0:
            print(f"(+) Habilidad '{nombre_recurso}' olvidada exitosamente.")
        else:
            print(f"(-) No se encontró la habilidad '{nombre_recurso}' para olvidar.")
        return resultado

if __name__ == '__main__':
    print("--- Probando el módulo KnowledgeBase ---")
    kb = KnowledgeBase()

    if kb.client: # Solo ejecutar si la conexión fue exitosa
        # Datos de prueba
        nombre_test = "api_prueba.com"
        datos_test = {
            "endpoint": "https://api_prueba.com/v1",
            "metodos": ["GET", "POST"],
            "ejemplo": "GET /v1/items",
            "contexto_aplicacion": ["General"]
        }

        # 1. Aprender la habilidad
        kb.aprender_habilidad(nombre_test, "API", datos_test)

        # 2. Conocer la habilidad
        habilidad_conocida = kb.conocer_habilidad(nombre_test)
        
        if habilidad_conocida:
            print("\n(+) Habilidad conocida:")
            print(habilidad_conocida)
            assert habilidad_conocida["datos"]["endpoint"] == "https://api_prueba.com/v1"
            print("\n(+) La aserción de datos fue exitosa.")
        else:
            print("(-) ERROR: No se pudo conocer la habilidad aprendida.")

        # 2.5 Probar la nueva función
        habilidades_contextuales = kb.conocer_habilidades_por_contexto(["General"])
        print("\n(+) Habilidades contextuales encontradas:")
        for h in habilidades_contextuales:
            print(f"  - {h['nombre_recurso']}")
        assert len(habilidades_contextuales) > 0
        print("\n(+) La aserción de contexto fue exitosa.")

        # 3. Olvidar la habilidad
        kb.olvidar_habilidad(nombre_test)
        print("\n--- Prueba completada ---")
    else:
        print("\n--- Prueba abortada por fallo de conexión ---")

```

---
path: listar_modelos.py
---
```py
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargar credenciales de forma segura
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("ERROR: No se encontró la GEMINI_API_KEY en el archivo .env")
else:
    try:
        genai.configure(api_key=gemini_api_key)
        
        print("Buscando modelos compatibles con 'generateContent'...")
        
        found_model = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_model = True
        
        if not found_model:
            print("No se encontraron modelos compatibles.")
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")

```

---
path: lock_manager.py
---
```py
import os
import time
import logging

LOCK_FILE = "control.lock"
LOCK_TIMEOUT = 15.0  # Segundos antes de considerar un bloqueo como obsoleto

logger = logging.getLogger("InteractIA")

def acquire_lock(agent_id):
    """Intenta adquirir el bloqueo de periféricos, esperando si es necesario."""
    logger.debug(f"[{agent_id}] Intentando adquirir el bloqueo...")
    while True:
        try:
            # Intenta crear el archivo en modo exclusivo. Si tiene éxito, tenemos el bloqueo.
            with os.fdopen(os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY), 'w') as f:
                f.write(f"{time.time()}|{agent_id}")
                logger.info(f"[{agent_id}] Bloqueo adquirido.")
                return # Bloqueo adquirido
        except FileExistsError:
            # El archivo ya existe, otro agente tiene el bloqueo. Hay que comprobar si está obsoleto.
            try:
                with open(LOCK_FILE, 'r') as f:
                    content = f.read().strip()
                    timestamp_str, owner_id = content.split('|', 1)
                    lock_time = float(timestamp_str)

                if time.time() - lock_time > LOCK_TIMEOUT:
                    logger.warning(f"[{agent_id}] Bloqueo obsoleto detectado (dueño: {owner_id}). Robando bloqueo...")
                    os.remove(LOCK_FILE) # Eliminar el bloqueo obsoleto
                    continue # Volver a intentar adquirir el bloqueo inmediatamente
                else:
                    # El bloqueo es válido, esperar un poco.
                    logger.debug(f"[{agent_id}] Esperando por bloqueo (dueño: {owner_id})...")
                    time.sleep(0.5)
            except (IOError, ValueError) as e:
                logger.error(f"[{agent_id}] Error al leer el archivo de bloqueo: {e}. Esperando...")
                time.sleep(0.5)

def release_lock(agent_id):
    """Libera el bloqueo de periféricos si se es el dueño."""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                content = f.read().strip()
                _, owner_id = content.split('|', 1)
            
            if owner_id == agent_id:
                os.remove(LOCK_FILE)
                logger.info(f"[{agent_id}] Bloqueo liberado.")
            else:
                logger.warning(f"[{agent_id}] Intentó liberar un bloqueo que no le pertenece (dueño: {owner_id}).")
    except (IOError, ValueError) as e:
        logger.error(f"[{agent_id}] Error al liberar el bloqueo: {e}")

```

---
path: logger_config.py
---
```py
import logging
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    """
    Formateador de logs que estructura la salida en formato JSON.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # Si hay datos extra, los añadimos al log
        if hasattr(record, 'extra_data'):
            log_record['extra_data'] = record.extra_data
        
        return json.dumps(log_record, ensure_ascii=False)

class GUIHandler(logging.Handler):
    """
    Un handler de logging que envía los registros a la GUI a través de un comunicador.
    """
    def __init__(self, comunicador):
        super().__init__()
        self.comunicador = comunicador

    def emit(self, record):
        msg = self.format(record)
        self.comunicador.log(msg)

def setup_logging(log_level=logging.DEBUG, comunicador=None):
    """
    Configura el sistema de logging para todo el proyecto.
    """
    logger = logging.getLogger("InteractIA")
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler for detailed DEBUG logs in JSON format
    file_handler = RotatingFileHandler("interactia_debug.log", maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # Ensure file handler captures DEBUG
    json_formatter = JsonFormatter()
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # Console handler for general INFO logs with a simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Console shows INFO and above
    simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # GUI handler
    if comunicador:
        gui_handler = GUIHandler(comunicador)
        gui_handler.setLevel(logging.INFO) # Only show INFO and above in the GUI
        gui_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)

if __name__ == '__main__':
    # Configurar el logging
    setup_logging(log_level=logging.DEBUG)
    
    # Obtener una instancia del logger
    test_logger = logging.getLogger("InteractIA")
    
    # Ejemplos de uso
    test_logger.debug("Este es un mensaje de depuración.")
    test_logger.info("El agente ha iniciado una nueva tarea.", extra={'extra_data': {'tarea_id': 123, 'objetivo': 'test'}})
    test_logger.warning("La confianza del OCR es baja.", extra={'extra_data': {'confianza': 45}})
    try:
        x = 1 / 0
    except ZeroDivisionError:
        test_logger.error("Error al realizar una división.", exc_info=True)
    
    print("\nLogs de prueba generados en 'interactia.log'")
```

---
path: main.py
---
```py
from interactia_gui import InteractIAGUI
import tkinter as tk
import sys
import threading
import random
import string
import argparse

def generar_id_aleatorio(longitud=6):
    """Genera un ID alfanumérico aleatorio."""
    caracteres = string.ascii_lowercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def main():
    """Punto de entrada principal para la aplicación InteractIA."""
    parser = argparse.ArgumentParser(description="InteractIA - Agente de IA Autónomo")
    parser.add_argument("--supervisando-a", type=str, help="El ID de la instancia de InteractIA a supervisar.")
    # Añadir aquí futuros argumentos de línea de comandos

    args, unknown = parser.parse_known_args()

    # Si se ejecuta con un objetivo desde la línea de comandos (sin GUI)
    if unknown:
        from agente import Agente
        # Este modo no tiene ID de ventana propio ni objetivo por ahora
        agente = Agente(callback_hablar=lambda msg: print(f"Agente: {msg}"))
        objetivo = " ".join(unknown)
        agente.establecer_objetivo(objetivo)
        agente.stream_run()
    else:
        # Modo GUI
        id_instancia = generar_id_aleatorio()
        titulo_ventana = f"interactia-{id_instancia}"

        root = tk.Tk()
        app = InteractIAGUI(root, titulo=titulo_ventana, id_objetivo=args.supervisando_a)
        root.mainloop()

if __name__ == "__main__":
    main()
```

---
path: memoria_chat_mongodb.py
---
```py
import pymongo
from config import (
    MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_CHAT_COLLECTION, 
    MONGODB_OPORTUNIDADES_COLLECTION, MONGODB_SESIONES_ANALIZADAS_COLLECTION,
    CHAT_HISTORY_LENGTH
)
import datetime
from datetime import timezone
import logging

class MongoDBChatMemory:
    """
    Gestiona el ciclo de vida completo de la memoria y el aprendizaje.
    - Almacena y recupera historiales de chat.
    - Genera resúmenes de contexto para el agente.
    - Gestiona una cola de "oportunidades de aprendizaje" extraídas de chats pasados.
    """
    def __init__(self, modelo):
        self.logger = logging.getLogger("InteractIA")
        self.modelo = modelo
        self.client = None
        self.db = None
        self.operativo = False

        try:
            if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
                raise ValueError("La URI de MongoDB no está configurada correctamente.")

            self.client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[MONGODB_DATABASE_NAME]
            
            # Colecciones principales
            self.collection_chats = self.db[MONGODB_CHAT_COLLECTION]
            self.collection_oportunidades = self.db[MONGODB_OPORTUNIDADES_COLLECTION]
            self.collection_sesiones_analizadas = self.db[MONGODB_SESIONES_ANALIZADAS_COLLECTION]
            self.collection_estado = self.db["estado_agentes"] # Nueva colección para el estado
            
            self.operativo = True
            self.logger.info(f"Memoria conectada a MongoDB. Gestionando 4 colecciones.")

        except Exception as e:
            self.logger.error(f"ERROR al inicializar MongoDBChatMemory: {e}")

    # --- MÉTODOS DE GESTIÓN DE CHAT ---

    def guardar_mensaje(self, session_key: str, role: str, content: dict):
        # ... (sin cambios respecto a la versión anterior)
        if not self.operativo: return None
        documento = {
            "session_key": session_key, "role": role, "content": content,
            "timestamp": datetime.datetime.now(timezone.utc)
        }
        try:
            return self.collection_chats.insert_one(documento).inserted_id
        except Exception as e:
            self.logger.error(f"Error al guardar mensaje: {e}")
            return None

    def _recuperar_historial_crudo(self, session_key: str, limit: int = 50):
        # ... (sin cambios, solo apunta a la nueva variable de colección)
        if not self.operativo: return []
        try:
            mensajes_cursor = self.collection_chats.find(
                {"session_key": session_key}
            ).sort("timestamp", pymongo.DESCENDING).limit(limit)
            historial = list(mensajes_cursor)
            historial.reverse()
            return historial
        except Exception as e:
            self.logger.error(f"Error al recuperar historial: {e}")
            return []

    def resumir_y_consultar(self, session_key: str, pregunta_concreta: str = None) -> str:
        """
        Genera un resumen inteligente del historial de chat o responde a una pregunta concreta.
        """
        if not self.operativo or not self.modelo:
            self.logger.warning("La memoria no puede resumir: no operativa o sin modelo de IA.")
            return "No hay contexto de memoria disponible."

        historial_crudo = self._recuperar_historial_crudo(session_key, limit=CHAT_HISTORY_LENGTH)
        if not historial_crudo:
            return "La conversación acaba de empezar. No hay historial previo."

        historial_str = "\n".join([f"{msg['role']}: {msg.get('content', {}).get('texto', '')}" for msg in historial_crudo])

        if pregunta_concreta:
            prompt_analisis = f"""
            Eres un analista de memoria. A partir del siguiente historial de conversación, responde de forma concisa a la pregunta específica del agente.
            
            PREGUNTA DEL AGENTE: "{pregunta_concreta}"
            
            HISTORIAL DE CONVERSACIÓN:
            {historial_str}
            
            RESPUESTA CONCISA:"""
        else:
            prompt_analisis = f"""
            Eres un analista de memoria. Tu tarea es leer el siguiente historial de conversación y generar un resumen de una o dos frases con los puntos clave para dar contexto a un agente de IA. 
            Extrae la intención principal del usuario, las entidades clave (ficheros, personas, temas), el último estado conocido y si hay alguna pregunta pendiente.
            
            HISTORIAL DE CONVERSACIÓN:
            {historial_str}
            
            RESUMEN DE CONTEXTO RELEVANTE:"""
        
        try:
            self.logger.info("Generando resumen de memoria...")
            respuesta = self.modelo.generate_content(prompt_analisis)
            resumen = respuesta.text.strip()
            self.logger.debug(f"Resumen de memoria generado: {resumen}")
            return resumen
        except Exception as e:
            self.logger.error(f"Error al generar resumen de memoria: {e}")
            return "Error al procesar la memoria."

    def convertir_historial_a_formato_simple(self, historial_complejo: list) -> list:
        """
        Convierte el historial con estructura compleja a la estructura simple que el agente usa internamente.
        """
        historial_simple = []
        for msg in historial_complejo:
            texto_contenido = msg.get('content', {}).get('texto', '')
            historial_simple.append({
                'rol': msg.get('role'),
                'contenido': texto_contenido
            })
        return historial_simple

    # --- MÉTODO PARA PUBLICAR ESTADO ---

    def publicar_estado_agente(self, session_key: str, estado_data: dict):
        """Publica el estado interno de un agente en una colección dedicada."""
        if not self.operativo: return
        try:
            # Añadir un timestamp al estado antes de guardarlo
            estado_data['timestamp'] = datetime.datetime.now(timezone.utc)
            
            self.collection_estado.update_one(
                {'_id': session_key},
                {'$set': estado_data},
                upsert=True
            )
            self.logger.debug(f"Estado del agente {session_key} publicado correctamente.")
        except Exception as e:
            self.logger.error(f"Error al publicar estado del agente {session_key}: {e}")

    # --- MÉTODOS PARA EL CICLO DE META-APRENDIZAJE ---

    def buscar_chat_sin_analizar(self):
        """Encuentra una session_key de un chat que aún no ha sido analizado para extraer conocimiento."""
        if not self.operativo: return None
        try:
            sesiones_analizadas = {s['session_key'] for s in self.collection_sesiones_analizadas.find({}, {'_id': 0, 'session_key': 1})}
            
            pipeline = [
                {'$group': {'_id': "$session_key"}},
                {'$match': {'_id': {'$nin': list(sesiones_analizadas)}}},
                {'$limit': 1}
            ]
            resultado = list(self.collection_chats.aggregate(pipeline))
            
            if resultado:
                session_key = resultado[0]['_id']
                self.logger.info(f"Chat sin analizar encontrado para meta-aprendizaje: {session_key}")
                return session_key
            else:
                self.logger.info("No se encontraron chats nuevos para analizar.")
                return None
        except Exception as e:
            self.logger.error(f"Error buscando chat sin analizar: {e}")
            return None

    def crear_oportunidades_de_aprendizaje(self, session_key: str, hipotesis: list):
        """Registra las habilidades potenciales encontradas en un chat en la cola de oportunidades."""
        if not self.operativo or not hipotesis: return
        
        nuevas_oportunidades = []
        for i, h in enumerate(hipotesis):
            oportunidad = {
                "oportunidad_id": f"{session_key}-skill-{i}",
                "fuente_session_id": session_key,
                "descripcion_hipotesis": h.get("descripcion", "Sin descripción"),
                "estado": "pendiente_verificacion",
                "fecha_creacion": datetime.datetime.now(timezone.utc)
            }
            nuevas_oportunidades.append(oportunidad)
        
        try:
            self.collection_oportunidades.insert_many(nuevas_oportunidades, ordered=False)
            self.logger.info(f"{len(nuevas_oportunidades)} nuevas oportunidades de aprendizaje creadas desde la sesión {session_key}.")
        except pymongo.errors.BulkWriteError as bwe:
            # Ignorar errores de clave duplicada si se re-analiza por alguna razón
            pass
        except Exception as e:
            self.logger.error(f"Error creando oportunidades de aprendizaje: {e}")

    def marcar_sesion_como_analizada(self, session_key: str):
        """Añade una session_key al registro de chats ya analizados para no volver a escanearlos."""
        if not self.operativo: return
        try:
            self.collection_sesiones_analizadas.update_one(
                {'session_key': session_key},
                {'$set': {'fecha_analisis': datetime.datetime.now(timezone.utc)}},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"Error marcando sesión como analizada: {e}")

    def obtener_oportunidad_pendiente(self):
        """Obtiene la siguiente habilidad potencial de la cola para ser procesada."""
        if not self.operativo: return None
        try:
            return self.collection_oportunidades.find_one_and_update(
                {"estado": "pendiente_verificacion"},
                {"$set": {"estado": "en_proceso_verificacion"}}
            )
        except Exception as e:
            self.logger.error(f"Error obteniendo oportunidad pendiente: {e}")
            return None

    def actualizar_estado_oportunidad(self, oportunidad_id: str, estado: str, datos_adicionales: dict = None):
        """Actualiza el estado de una oportunidad de aprendizaje."""
        if not self.operativo: return
        try:
            update_doc = {"$set": {"estado": estado}}
            if datos_adicionales:
                update_doc["$set"].update(datos_adicionales)
            
            self.collection_oportunidades.update_one(
                {"oportunidad_id": oportunidad_id},
                update_doc
            )
        except Exception as e:
            self.logger.error(f"Error actualizando estado de oportunidad: {e}")

```

---
path: mover_mouse.py
---
```py
import pyautogui
import time

# Desactivamos el fail-safe, ya que es necesario para la ejecucin desatendida
# donde el estado del cursor puede ser impredecible durante la desconexin.
pyautogui.FAILSAFE = False

def mover_y_capturar():
    """
    Mueve el ratón, espera un momento y luego toma una captura de pantalla como prueba.
    """
    try:
        # Damos unos segundos para que el script se inicie despus de la desconexin
        print("Iniciando en 5 segundos...")
        time.sleep(5)

        # Mover el ratón a una posición visible
        x, y = 500, 500
        print(f"Moviendo el ratón a ({x}, {y}).")
        pyautogui.moveTo(x, y, duration=2)

        # Esperar un segundo para asegurar que el movimiento se complete
        time.sleep(1)

        # Tomar la captura de pantalla como prueba
        nombre_archivo = "prueba_movimiento.png"
        print(f"Tomando captura de pantalla y guardando como '{nombre_archivo}'.")
        pyautogui.screenshot(nombre_archivo)

        print("¡Operación completada! Puedes reconectarte para verificar el archivo.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    mover_y_capturar()

```

---
path: show_skills.py
---
```py
from knowledge_base import KnowledgeBase
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

kb = KnowledgeBase()
skills = kb.get_all_skills()

print(json.dumps(skills, indent=4, cls=DateTimeEncoder))
```

---
path: verificar_credenciales.py
---
```py
import os
from dotenv import load_dotenv
import pymongo
import google.generativeai as genai

def verificar_credenciales():
    """
    Carga las credenciales desde el archivo .env y prueba las conexiones
    a MongoDB y a la API de Gemini.
    """
    print("Cargando credenciales desde el archivo .env...")
    load_dotenv()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")

    if not gemini_api_key or "SU_API_KEY" in gemini_api_key:
        print("(-) ERROR: La API Key de Gemini no se ha encontrado o no se ha modificado en el archivo .env")
    else:
        print("(+) Credencial de Gemini encontrada.")
        try:
            genai.configure(api_key=gemini_api_key)
            # Hacemos una llamada simple para verificar que la clave es válida
            models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if models:
                print("(+) Conexión con la API de Gemini exitosa.")
            else:
                print("(-) ERROR: La API Key de Gemini parece válida, pero no se encontraron modelos compatibles.")
        except Exception as e:
            print(f"(-) ERROR al conectar con la API de Gemini: {e}")

    print("-" * 20)

    if not mongo_uri or "SU_CADENA_DE_CONEXION" in mongo_uri:
        print("(-) ERROR: La URI de MongoDB no se ha encontrado o no se ha modificado en el archivo .env")
    else:
        print("(+) Credencial de MongoDB encontrada.")
        try:
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # El comando ping es la forma estándar de probar una conexión
            client.admin.command('ping')
            print("(+) Conexión con MongoDB exitosa.")
        except pymongo.errors.ConnectionFailure as e:
            print(f"(-) ERROR de conexión con MongoDB: {e}")
        except pymongo.errors.ConfigurationError as e:
            print(f"(-) ERROR de configuración de MongoDB (revisa la cadena de conexión): {e}")
        except Exception as e:
            print(f"(-) ERROR inesperado al conectar con MongoDB: {e}")

if __name__ == "__main__":
    verificar_credenciales()

```

---
path: vision.py
---
```py
import pyautogui
from PIL import Image, ImageDraw
import logging
import pytesseract
import subprocess
import os

def buscar_tesseract():
    """
    Busca el ejecutable de Tesseract en las rutas de instalación más comunes.
    Devuelve la ruta completa si lo encuentra, de lo contrario None.
    """
    print("Buscando Tesseract OCR...")
    rutas_comunes = [
        "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
    ]

    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            print(f"(+) Tesseract encontrado en: {ruta}")
            return ruta

    print("(-) Tesseract no se encontró en las rutas de instalación comunes.")
    return None

class Vision:
    """
    Clase encargada de la percepción del entorno, incluyendo captura de pantalla y OCR.
    """
    def __init__(self):
        self.logger = logging.getLogger("InteractIA")
        try:
            tesseract_path = buscar_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                self.logger.info(f"Usando Tesseract desde la ruta: {tesseract_path}")
            else:
                self.logger.warning("Tesseract no encontrado. El OCR no estará disponible.")
        except Exception as e:
            self.logger.error(f"Error al configurar Pytesseract. Asegúrate de que Tesseract está instalado. Error: {e}", exc_info=True)

    def capturar_entorno(self, id_ventana_propia=None):
        """Captura la pantalla completa y opcionalmente oculta la ventana propia del agente."""
        self.logger.debug("Capturando el entorno.")
        captura_completa = pyautogui.screenshot()

        if id_ventana_propia:
            try:
                ventanas = pyautogui.getWindowsWithTitle(id_ventana_propia)
                if ventanas:
                    ventana_propia = ventanas[0]
                    draw = ImageDraw.Draw(captura_completa)
                    # Dibuja un rectángulo negro sobre la ventana propia
                    draw.rectangle(
                        (ventana_propia.left, ventana_propia.top, ventana_propia.right, ventana_propia.bottom),
                        fill='black'
                    )
                    self.logger.info(f"Ocultada la ventana propia: '{id_ventana_propia}'")
                else:
                    self.logger.warning(f"No se encontró la ventana propia para ocultar: '{id_ventana_propia}'")
            except Exception as e:
                self.logger.error(f"Error al ocultar la ventana propia '{id_ventana_propia}': {e}")

        return captura_completa

    def capturar_ventana_objetivo(self, titulo_objetivo):
        """Captura únicamente la región de una ventana objetivo específica."""
        self.logger.debug(f"Intentando capturar la ventana objetivo: {titulo_objetivo}")
        try:
            ventanas = pyautogui.getWindowsWithTitle(titulo_objetivo)
            if ventanas:
                ventana = ventanas[0]
                captura_ventana = pyautogui.screenshot(region=(ventana.left, ventana.top, ventana.width, ventana.height))
                self.logger.info(f"Capturada la ventana objetivo: '{titulo_objetivo}'")
                return captura_ventana
            else:
                self.logger.warning(f"No se encontró ninguna ventana con el título: '{titulo_objetivo}'")
                return None
        except Exception as e:
            self.logger.error(f"Error al capturar la ventana '{titulo_objetivo}': {e}")
            return None

    def guardar_imagen(self, imagen: Image.Image, nombre_archivo: str):
        self.logger.info(f"Guardando imagen en '{nombre_archivo}'.", extra={'extra_data': {'archivo': nombre_archivo}})
        imagen.save(nombre_archivo)

    def leer_texto_en_pantalla(self, imagen: Image.Image):
        """
        Utiliza OCR para extraer texto y sus coordenadas de una imagen.

        Args:
            imagen (PIL.Image.Image): La imagen de la que extraer el texto.

        Returns:
            list: Una lista de diccionarios, donde cada uno representa un bloque de texto detectado.
        """
        self.logger.info("Realizando OCR para leer texto en la imagen.")
        try:
            # Usamos image_to_data para obtener texto, coordenadas y confianza
            data = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT)
            
            bloques = []
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                # Filtramos los resultados con una confianza mínima (ej. 60%)
                confianza = int(data['conf'][i])
                if confianza > 60:
                    texto = data['text'][i].strip()
                    if texto: # Nos aseguramos de que no sea solo espacio en blanco
                        bloque = {
                            'texto': texto,
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': confianza
                        }
                        bloques.append(bloque)
            
            self.logger.info(f"OCR completado. Se encontraron {len(bloques)} bloques de texto con confianza > 60%.")
            return bloques
        except pytesseract.TesseractNotFoundError:
            self.logger.error("Tesseract no encontrado. Asegúrate de que está instalado y la ruta es correcta.", exc_info=True)
            return []
        except Exception as e:
            self.logger.error(f"Ocurrió un error durante el OCR: {e}", exc_info=True)
            return []

    def leer_texto_ventana_activa(self):
        """
        Captura la ventana activa y extrae el texto de ella.

        Returns:
            list: Una lista de diccionarios con el texto extraído.
        """
        self.logger.info("Leyendo texto de la ventana activa.")
        try:
            ventana = pyautogui.getActiveWindow()
            if not ventana:
                self.logger.warning("No se pudo obtener la ventana activa.")
                return []
            
            captura = pyautogui.screenshot(region=(ventana.left, ventana.top, ventana.width, ventana.height))
            return self.leer_texto_en_pantalla(captura)
        except Exception as e:
            self.logger.error(f"Error al leer el texto de la ventana activa: {e}", exc_info=True)
            return []

if __name__ == '__main__':
    from logger_config import setup_logging
    setup_logging(log_level=logging.DEBUG)
    main_logger = logging.getLogger("InteractIA")

    main_logger.info("--- Iniciando prueba del Módulo de Visión con OCR ---")
    vision = Vision()

    # 1. Capturar la pantalla
    captura_completa, captura_ventana = vision.capturar_pantalla("Explorador de archivos")
    if captura_completa:
        vision.guardar_imagen(captura_completa, "prueba_vision_completa.png")
    if captura_ventana:
        vision.guardar_imagen(captura_ventana, "prueba_vision_ventana.png")

    # 2. Leer el texto de la pantalla
    if captura_ventana:
        datos_texto = vision.leer_texto_en_pantalla(captura_ventana)
        if datos_texto:
            main_logger.info("Se ha detectado el siguiente texto en la ventana (primeros 5 bloques):")
            for bloque in datos_texto[:5]:
                # Usamos pprint para una mejor visualización del diccionario
                import pprint
                pprint.pprint(bloque)
        else:
            main_logger.warning("No se detectó texto en la ventana o Tesseract no está configurado correctamente.")

    main_logger.info("--- Prueba de Visión finalizada ---")

```

