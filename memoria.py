import pymongo
from config import (
    MONGO_URI, MONGODB_DATABASE_NAME, MONGODB_CHAT_COLLECTION, MONGODB_KB_COLLECTION,
    CHAT_HISTORY_LENGTH
)
import datetime
from datetime import timezone
import logging
from model_manager import get_model_provider, ModelProvider

class MongoDBChatMemory:
    def __init__(self, model_provider: ModelProvider = None):
        self.logger = logging.getLogger("InteractIA")
        self.model_provider = model_provider
        self.client = None
        self.db = None
        self.operativo = False

        try:
            if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
                raise ValueError("La URI de MongoDB no está configurada.")

            self.client = pymongo.MongoClient(MONGO_URI)
            self.client.admin.command('ping')
            self.db = self.client[MONGODB_DATABASE_NAME]
            
            self.collection_chats = self.db[MONGODB_CHAT_COLLECTION]
            self.kb_collection = self.db[MONGODB_KB_COLLECTION]
            
            self.operativo = True
            self.logger.info("Memoria conectada a MongoDB.")

        except Exception as e:
            self.logger.error(f"ERROR al inicializar MongoDBChatMemory: {e}")

    def convertir_historial_a_formato_simple(self, historial_raw: list) -> list:
        historial_simple = []
        for msg in historial_raw:
            rol = msg.get('role')
            contenido = msg.get('content', {}).get('texto', '')
            if rol and contenido:
                historial_simple.append({'rol': rol, 'contenido': contenido})
        return historial_simple

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
            respuesta_modelo = self.model_provider.generate_content(prompt_analisis)
            
            if isinstance(respuesta_modelo, dict):
                resumen = respuesta_modelo.get('text', str(respuesta_modelo))
            else:
                resumen = str(respuesta_modelo)

            self.logger.debug(f"Resumen de memoria generado: {resumen}")
            return resumen
        except Exception as e:
            self.logger.error(f"Error al generar resumen de memoria: {e}", exc_info=True)
            return "Error al procesar la memoria."

    def get_chat_history(self, session_key: str, limit: int = 50) -> list:
        self.logger.info(f"Recuperando historial de chat para la sesión {session_key} (límite: {limit}).")
        return self._recuperar_historial_crudo(session_key, limit)

    def query_base_conocimiento(self, query: str, top_k: int = 3) -> str:
        """
        Realiza una búsqueda semántica en la base de conocimiento.
        """
        if not self.operativo:
            return "Error: La memoria no está operativa."
        
        if not self.model_provider:
            # Si no se pasó un proveedor, obtenemos el por defecto
            try:
                self.model_provider = get_model_provider()
            except Exception as e:
                self.logger.error(f"Error al obtener el proveedor de modelos para la KB: {e}")
                return "Error: No se pudo inicializar el proveedor de modelos para la KB."

        self.logger.info(f"Realizando búsqueda en la KB con la consulta: '{query}'")
        try:
            # 1. Generar el embedding para la consulta del usuario
            query_embedding = self.model_provider.embed_content(query)
            if not query_embedding:
                return "Error: No se pudo generar el embedding para la consulta."

            # 2. Construir y ejecutar el pipeline de búsqueda vectorial
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": 10,
                        "limit": top_k
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "text": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(self.kb_collection.aggregate(pipeline))

            if not results:
                return "No se encontraron resultados relevantes en la base de conocimiento."

            # 3. Formatear y devolver los resultados
            contexto = "\n\n---\n".join([res['text'] for res in results])
            self.logger.info(f"Búsqueda en KB completada. Se encontraron {len(results)} resultados.")
            return f"Aquí hay algunos fragmentos de la documentación que podrían ser relevantes:\n\n{contexto}"

        except Exception as e:
            self.logger.error(f"Error durante la búsqueda en la base de conocimiento: {e}", exc_info=True)
            return "Error al consultar la base de conocimiento."

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