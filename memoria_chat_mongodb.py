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
