import pymongo
from config import (
    MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_CHAT_COLLECTION, 
    MONGODB_OPORTUNIDADES_COLLECTION, MONGODB_SESIONES_ANALIZADAS_COLLECTION,
    CHAT_HISTORY_LENGTH
)
import datetime
from datetime import timezone
import logging
from model_manager import ModelProvider # Importar la clase base

class MongoDBChatMemory:
    def __init__(self, model_provider: ModelProvider = None):
        self.logger = logging.getLogger("InteractIA")
        self.model_provider = model_provider # Usar el proveedor genérico
        self.client = None
        self.db = None
        self.operativo = False

        try:
            if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
                raise ValueError("La URI de MongoDB no está configurada.")

            self.client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[MONGODB_DATABASE_NAME]
            
            self.collection_chats = self.db[MONGODB_CHAT_COLLECTION]
            self.collection_oportunidades = self.db[MONGODB_OPORTUNIDADES_COLLECTION]
            self.collection_sesiones_analizadas = self.db[MONGODB_SESIONES_ANALIZADAS_COLLECTION]
            self.collection_estado = self.db["estado_agentes"]
            
            self.operativo = True
            self.logger.info("Memoria conectada a MongoDB.")

        except Exception as e:
            self.logger.error(f"ERROR al inicializar MongoDBChatMemory: {e}")

    def resumir_y_consultar(self, session_key: str, pregunta_concreta: str = None) -> str:
        if not self.operativo or not self.model_provider:
            self.logger.warning("La memoria no puede resumir: no operativa o sin proveedor de modelo.")
            return "No hay contexto de memoria disponible."

        historial_crudo = self._recuperar_historial_crudo(session_key, limit=CHAT_HISTORY_LENGTH)
        if not historial_crudo:
            return "La conversación acaba de empezar."

        historial_str = "\n".join([f"{msg['role']}: {msg.get('content', {}).get('texto', '')}" for msg in historial_crudo])

        if pregunta_concreta:
            prompt_analisis = f'''
            Eres un analista de memoria. Responde concisamente a la pregunta del agente basándote en el historial.
            PREGUNTA: "{pregunta_concreta}"
            HISTORIAL:
            {historial_str}
            RESPUESTA CONCISA:'''
        else:
            prompt_analisis = f'''
            Eres un analista de memoria. Resume en una o dos frases los puntos clave del siguiente historial para dar contexto a un agente de IA.
            Extrae la intención principal, entidades clave, último estado y preguntas pendientes.
            HISTORIAL:
            {historial_str}
            RESUMEN DE CONTEXTO RELEVANTE:'''
        
        try:
            self.logger.info("Generando resumen de memoria...")
            # Usar el nuevo método del proveedor
            resumen = self.model_provider.generate_text(prompt_analisis)
            self.logger.debug(f"Resumen de memoria generado: {resumen}")
            return resumen
        except Exception as e:
            self.logger.error(f"Error al generar resumen de memoria: {e}")
            return "Error al procesar la memoria."

    # ... (El resto de los métodos de la clase permanecen sin cambios)
    def guardar_mensaje(self, session_key: str, role: str, content: dict):
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

    def convertir_historial_a_formato_simple(self, historial_complejo: list) -> list:
        historial_simple = []
        for msg in historial_complejo:
            texto_contenido = msg.get('content', {}).get('texto', '')
            historial_simple.append({
                'rol': msg.get('role'),
                'contenido': texto_contenido
            })
        return historial_simple

    def publicar_estado_agente(self, session_key: str, estado_data: dict):
        if not self.operativo: return
        try:
            estado_data['timestamp'] = datetime.datetime.now(timezone.utc)
            self.collection_estado.update_one(
                {'_id': session_key},
                {'$set': estado_data},
                upsert=True
            )
        except Exception as e:
            self.logger.error(f"Error al publicar estado del agente {session_key}: {e}")