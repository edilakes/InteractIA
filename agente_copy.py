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
        
        try:
            self.model_provider.set_model(model_name)
            self.logger.info(f"Modelo '{model_name}' establecido en el proveedor.")
        except Exception as e:
            self.logger.critical(f"¡ERROR CRÍTICO! No se pudo establecer el modelo '{model_name}' en el proveedor: {e}")
            self.operativo = False
            return

        self.mi_id_ventana = id_ventana
        self.resultado_accion_anterior = None
        self.parada_emergencia = threading.Event()
        self.esperando_respuesta_usuario = False

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

        # Definición de la caja de herramientas
        self.herramientas = {
            "hablar": self._ejecutar_accion_comunicacion,
            "finalizar": self._ejecutar_accion_comunicacion,
            "pedir_aclaracion": self._ejecutar_accion_comunicacion,
            "vision.leer_texto_en_pantalla": self.vision.leer_texto_en_pantalla,
            "vision.leer_texto_ventana_activa": self.vision.leer_texto_ventana_activa,
            "controlador.clic": self.controlador.clic,
            "controlador.escribir": self.controlador.escribir,
            "controlador.presionar_tecla": self.controlador.presionar_tecla,
            "controlador.mantener_tecla": self.controlador.mantener_tecla,
            "controlador.soltar_tecla": self.controlador.soltar_tecla,
            "controlador.scroll": self.controlador.scroll,
            "controlador.mouse_down": self.controlador.mouse_down,
            "controlador.mouse_up": self.controlador.mouse_up,
            "controlador.arrastrar_a": self.controlador.arrastrar_a,
            "controlador.esperar": self.controlador.esperar,
            "controlador.mover_raton": self.controlador.mover_raton,
            "controlador.enfocar_ventana": self.controlador.enfocar_ventana
        }

    def detener_proceso_emergencia(self):
        self.parada_emergencia.set()
        self.logger.warning("¡PARADA DE EMERGENCIA ACTIVADA!")

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
        
        self.logger.debug(f"Cadena JSON extraída: '{json_str}'")
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error al decodificar JSON: {e}. Contenido: '{json_str}'")
            return {"plan": [], "razon": f"Error de decodificación JSON en la respuesta: {e}", "respuesta_original": json_str}

    def _call_model(self, prompt: str, image=None) -> dict:
        self.logger.info("Esperando el bloqueo de la API del modelo...")
        with model_api_lock:
            self.logger.info("Bloqueo adquirido. Enviando petición al modelo de IA...")
            try:
                respuesta_bruta = self.model_provider.generate_content(prompt, image)
                self.logger.debug(f"Respuesta BRUTA del modelo: {respuesta_bruta}")

                if isinstance(respuesta_bruta, dict) and 'plan' in respuesta_bruta:
                    decision = respuesta_bruta
                else:
                    texto_para_parsear = None
                    if isinstance(respuesta_bruta, dict) and 'text' in respuesta_bruta:
                        texto_para_parsear = respuesta_bruta['text']
                    elif isinstance(respuesta_bruta, str):
                        texto_para_parsear = respuesta_bruta
                    
                    if not texto_para_parsear:
                        self.logger.error("La respuesta del modelo está vacía o en un formato inesperado.")
                        return {"plan": [], "razon": "Respuesta vacía o inesperada del modelo.", "respuesta_original": str(respuesta_bruta)}

                    decision = self._limpiar_y_parsear_json(texto_para_parsear)
                
                if "plan" not in decision:
                     self.logger.warning(f"El JSON parseado no contiene un 'plan'. Respuesta original: {texto_para_parsear}")
                     if "respuesta_original" not in decision:
                         decision["respuesta_original"] = texto_para_parsear
                return decision

            except Exception as e:
                self.logger.error(f"ERROR al llamar al proveedor del modelo de IA: {e}", exc_info=True)
                return {"plan": [], "razon": f"Error en la llamada a la API a través del proveedor: {e}"}

    def establecer_objetivo(self, objetivo):
        self.logger.info(f"Llamada a establecer_objetivo con: '{objetivo}'")
        self.esperando_respuesta_usuario = False
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
        self.logger.info("--- Fase: Observar ---")
        captura = self.vision.capturar_entorno(id_ventana_propia=self.mi_id_ventana)
        return {'captura': captura}

    def pensar(self, estado_observado: dict):
        self.logger.info("--- Fase: Pensar ---")
        if not self.objetivo:
            return {"plan": [{"herramienta": "finalizar", "params": {"razon": "No hay objetivo"}}] }
        
        resumen_memoria = self.memoria.resumir_y_consultar(session_key=self.mi_id_ventana)
        
        prompt = self._construir_prompt_herramientas(
            resumen_memoria=resumen_memoria,
            feedback_anterior=self.resultado_accion_anterior
        )
        return self._call_model(prompt, estado_observado['captura'])

    def _construir_prompt_herramientas(self, resumen_memoria: str, feedback_anterior=None):
        contexto_feedback = ""
        if feedback_anterior:
            estado = "ÉXITO" if feedback_anterior['exito'] else "FALLO"
            contexto_feedback = f"RESULTADO DEL PLAN ANTERIOR: {estado}. Razón: {feedback_anterior['razon']}.\n"
            if not feedback_anterior['exito']:
                contexto_feedback += "Debes re-evaluar y probar un enfoque diferente."

        prompt = f'''
Tu rol es InteractIA, un agente de IA que completa tareas controlando un ordenador.
Tu proceso se basa en un ciclo de **Observar, Pensar, Actuar**.

**REGLA FUNDAMENTAL: Antes de usar `controlador.clic`, DEBES usar una herramienta de visión para encontrar las coordenadas del elemento. NO inventes coordenadas.**

**OBJETIVO ACTUAL:** '{self.objetivo}'

{contexto_feedback}

**CONTEXTO DE MEMORIA RELEVANTE:**
{resumen_memoria}

**CAJA DE HERRAMIENTAS DISPONIBLES:**
Tu única forma de interactuar con el sistema es a través de un plan compuesto por las siguientes herramientas PRIMITIVAS.

*** Herramientas de Percepción (Visión) ***
- `vision.leer_texto_en_pantalla(imagen)`: Analiza la imagen de pantalla proporcionada y devuelve una lista de objetos, cada uno con el texto encontrado y sus coordenadas (`texto`, `left`, `top`, `width`, `height`). Esencial para localizar elementos.
- `vision.leer_texto_ventana_activa()`: Realiza la misma función que la anterior pero solo en la ventana que está activa en ese momento.

*** Herramientas de Acción (Controlador) ***
- `controlador.clic(x, y, boton="left")`: Hace clic en las coordenadas (x, y) de la pantalla.
- `controlador.escribir(texto)`: Escribe el texto proporcionado.
- `controlador.presionar_tecla(tecla)`: Presiona una tecla (ej: "enter", "esc") o una combinación (ej: "ctrl+c").
- `controlador.mantener_tecla(tecla)`: Mantiene presionada una tecla del teclado (ej: "alt").
- `controlador.soltar_tecla(tecla)`: Suelta una tecla del teclado.
- `controlador.scroll(clics)`: Hace scroll. `clics` positivo es hacia arriba, `clics` negativo es hacia abajo.
- `controlador.mover_raton(x, y)`: Mueve el cursor a las coordenadas (x, y).
- `controlador.mouse_down(boton="left")`: Mantiene presionado un botón del ratón.
- `controlador.mouse_up(boton="left")`: Suelta un botón del ratón.
- `controlador.arrastrar_a(x, y, duracion=1.0)`: Arrastra el ratón a las coordenadas (x, y) mientras mantiene el botón presionado.
- `controlador.enfocar_ventana(titulo)`: Activa la ventana que contenga el texto del título.
- `controlador.esperar(segundos)`: Pausa la ejecución durante los segundos especificados.

*** Herramientas de Comunicación ***
- `hablar(mensaje)`: Responde verbalmente al usuario. Úsalo si la tarea pide una respuesta directa.
- `finalizar(razon)`: Da por completado el objetivo actual, informando de la razón.

**TAREA PRINCIPAL:**
Tu deber es analizar la captura de pantalla, el objetivo y el feedback para crear un plan de acción.
El plan es una secuencia de llamadas a las herramientas de tu caja. El agente debe ser capaz de componer secuencias complejas (ej. alt+tab) por sí mismo.

**RESPUESTA (ÚNICAMENTE JSON con la siguiente estructura obligatoria):**
```json
{
  "pensamiento": "<Tu razonamiento para elegir este plan. Describe tu estrategia paso a paso. Piensa en cómo usar la visión para encontrar coordenadas antes de actuar. >",
  "plan": [
    {
      "herramienta": "<nombre_de_la_herramienta>",
      "params": {" <nombre_param>": "<valor_param>" },
      "variable_salida": "<nombre_opcional_para_guardar_el_resultado>"
    }
  ]
}
```
**IMPORTANTE:** Para usar el resultado de un paso anterior (ej. `vision.leer_texto_en_pantalla`) en un paso posterior (ej. `controlador.clic`), guarda el resultado en una `variable_salida` y luego refiérete a ella con `@nombre_variable` en los parámetros. Usa notación de corchetes para acceder a índices y claves (ej: `@mi_var[0]['clave']`).
'''
        return prompt

    def _resolver_valor(self, valor, resultados_pasos):
        if not isinstance(valor, str) or not valor.startswith('@'):
            return valor

        # Expresión regular para encontrar todas las variables y sus accesos
        # Ejemplo: @var1[0]['key'] + @var2 / 2
        expresion_completa = valor
        
        # Regex para encontrar todas las ocurrencias de @variable[...]['...']
        matches = re.finditer(r'@(\w+)(.*)', expresion_completa)
        
        for match in reversed(list(matches)):
            var_name, path = match.groups()
            
            if var_name not in resultados_pasos:
                raise ValueError(f"Variable '{var_name}' no encontrada en los resultados.")

            # Valor inicial de la variable
            resolved_value = resultados_pasos[var_name]
            
            # Procesar el path (simplificado por ahora)
            # Ejemplo de path: [?(@['texto'].includes('Buscar'))][0]['left']
            
            # 1. Filtro (ej: [?(@['texto'].includes('Buscar'))])
            filter_match = re.search(r