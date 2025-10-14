# Flujo de Entrenamiento de InteractIA

Este documento sirve como hoja de ruta y registro de nuestro progreso en el entrenamiento del agente InteractIA.

## Estado Actual

- **Nivel Actual:** Nivel 2: Interacción Básica con el SO.
- **Próximo Objetivo:** Completar la prueba final del Nivel 2.

---
## Plan de Aprendizaje Evolutivo para InteractIA (Versión 2)

**Objetivo Final:** Convertir a InteractIA en un agente autónomo capaz de emular las acciones de un usuario humano en un ordenador, utilizando únicamente la visión de pantalla, el teclado y el ratón para realizar tareas complejas y aprender de forma continua.

### Metodología de Entrenamiento: Ciclo Interactivo Supervisado

Para cada nueva habilidad que enseñemos, seguiremos un ciclo de 4 pasos:

1.  **Propuesta (Yo, Gemini):** Diseñaré y te propondré un `prompt` específico para enseñarle a InteractIA una nueva tarea o concepto, enmarcado en el nivel de aprendizaje en el que estemos.
2.  **Ejecución (Tú, Usuario):** Introducirás el `prompt` exacto en la instancia de InteractIA.
3.  **Verificación (Ambos):** Observaremos la respuesta y las acciones de InteractIA para determinar si ha cumplido el objetivo del `prompt` correctamente.
4.  **Análisis y Aprendizaje (Ambos):**
    *   **Si tiene éxito:** Verificaremos que la nueva habilidad o conocimiento se ha guardado correctamente en su base de conocimiento (la colección `habilidades`).
    *   **Si falla:** Analizaremos el motivo del fallo (ej: mala interpretación del prompt, error en la ejecución de acciones, fallo en la visión) y lo usaremos para depurar y refinar el `prompt` o la lógica subyacente del agente.

Este ciclo nos permitirá avanzar de forma segura y medible.

---
### La Escalera de Aprendizaje

#### Nivel 0: Fundamentos - El Cuerpo Digital (Ya Existente)
*   **Estado:** Completado. Las acciones básicas (`clic`, `escribir`, etc.) ya funcionan.

---

#### Nivel 1: Conciencia del Entorno - "Ver y Etiquetar"
*   **Estado:** COMPLETADO.
*   **Objetivo:** Que el agente identifique y catalogue los elementos de la interfaz gráfica (widgets).
*   **Logros:**
    *   El agente puede analizar la pantalla y generar un JSON con los elementos visibles.
    *   Se ha depurado un error en `agente.py` que impedía el correcto procesamiento de respuestas JSON de tipo lista.

---

#### Nivel 2: Interacción Básica con el SO - El "ABC" de Windows
*   **Estado:** EN PROGRESO.
*   **Objetivo:** Dominar la gestión de ventanas y archivos basándose en la visión, incluyendo la verificación de los resultados de sus acciones.
*   **Proceso de Entrenamiento (Ciclo Interactivo):
    1.  **[COMPLETADO]** **Propuesta:** Se propuso al agente hacer clic en el icono "Este equipo".
    2.  **[COMPLETADO]** **Ejecución:** El agente ejecutó la tarea.
    3.  **[COMPLETADO]** **Verificación:** El agente determinó correctamente que el icono no estaba visible y pidió aclaraciones.
    4.  **[COMPLETADO]** **Análisis:** Se concluyó que el comportamiento fue el esperado.
    5.  **[COMPLETADO]** **Propuesta 2:** Se propuso al agente usar la combinación de teclas `win+d` para minimizar las ventanas.
    6.  **[COMPLETADO]** **Ejecución y Fallo:** La acción falló, revelando un bug en la gestión de combinaciones de teclas.
    7.  **[COMPLETADO]** **Depuración:** Se ha corregido la función `presionar_tecla` en `controlador.py` para que use `pyautogui.hotkey()` y se ha robustecido la función `actuar` en `agente.py`.
    8.  **[COMPLETADO]** **Verificación y Depuración de Bucle:** Se detectó un bucle de razonamiento. Se ha enseñado al agente a verificar el resultado de sus acciones y a usar la acción `hablar` para comunicar resultados.
    9.  **[PENDIENTE]** **Prueba Final Nivel 2:** Se propondrá al agente hacer clic en un icono del escritorio ('Papelera de reciclaje') para confirmar que puede actuar sobre los elementos que observa.
        *   **Próximo Prompt:** 'Excelente. Has usado `hablar` correctamente y me has dado la lista de iconos. Ahora, haz clic en el icono con el nombre "Papelera de reciclaje".'

---

#### Nivel 3: Uso de Aplicaciones Comunes - Herramientas del Oficio
*   **Objetivo:** Aprender a usar un navegador, un editor de texto y una terminal.
*   **Proceso de Entrenamiento (Ciclo Interactivo):
    1.  **Propuesta:** Empezaremos con algo como: "Abre el navegador y busca 'InteractIA en GitHub'".
    2.  **Ejecución:** Se lo pedirás.
    3.  **Verificación:** Veremos si abre el navegador, escribe en la barra de búsqueda y ejecuta la búsqueda.
    4.  **Análisis:** Si se atasca (ej: no sabe dónde está la barra de búsqueda), le daremos un prompt más específico para que aprenda a identificarla, creando una nueva sub-habilidad.

---

#### Nivel 4: Composición de Tareas y Planificación - "Resolviendo Problemas"
*   **Objetivo:** Descomponer un objetivo complejo dictado por el usuario en una secuencia de pasos lógicos.
*   **Proceso de Entrenamiento (Ciclo Interactivo):
    1.  **Propuesta:** Te daré un objetivo complejo: "Busca la documentación de la API de Gemini, copia el ejemplo de código para listar modelos y pégalo en un nuevo archivo".
    2.  **Ejecución:** Le plantearás el objetivo.
    3.  **Verificación:** Observaremos si el agente es capaz de generar un plan de pasos y ejecutarlo.
    4.  **Análisis:** Aquí es clave ver cómo razona. Si su plan es ilógico, le daremos pistas con un nuevo prompt para corregir su razonamiento. Celebraremos y guardaremos los planes exitosos como nuevas habilidades compuestas.

---

#### Nivel 5: Autonomía y Auto-corrección - "Pensamiento Crítico"
*   **Objetivo:** Que el agente pueda detectar sus propios errores y intentar solucionarlos.
*   **Proceso de Entrenamiento (Ciclo Interactivo):
    1.  **Propuesta:** Crearemos escenarios de fallo. Por ejemplo: "Intenta guardar un archivo en una carpeta protegida".
    2.  **Ejecución:** Le darás la tarea.
    3.  **Verificación:** Veremos el error de "permiso denegado" y observaremos la reacción del agente.
    4.  **Análisis:** Inicialmente, el agente fallará y se detendrá. Le daremos un nuevo prompt: "Cuando veas un error de 'permiso denegado', debes notificar al usuario y finalizar la tarea. Guarda este aprendizaje". Así, crearemos una nueva "habilidad de recuperación".

---
## Scripts de Asistencia al Entrenamiento

Estos scripts son herramientas de apoyo utilizadas por el asistente (Gemini) para depurar y verificar el estado del agente. No forman parte del código fuente de InteractIA.

### `get_chat_history.py`

Este script se conecta a la base de datos de MongoDB y recupera el historial de chat de una sesión específica.

```python
import os
import pymongo
from dotenv import load_dotenv
import datetime
import argparse

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ---
# Configuración
# ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"
MONGODB_CHAT_COLLECTION = "chat_history"

# ---
# Script
# ---
def get_chat_history(session_id):
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
        return

    try:
        print(f"Conectando a MongoDB con la URI proporcionada...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        collection_chats = db[MONGODB_CHAT_COLLECTION]
        print("Conexión exitosa.")

        print(f"Buscando historial de chat para la sesión: {session_id}...")
        mensajes_cursor = collection_chats.find(
            {"session_key": session_id}
        ).sort("timestamp", pymongo.ASCENDING)

        historial = list(mensajes_cursor)

        if not historial:
            print(f"No se encontró historial de chat para la sesión '{session_id}'.")
        else:
            print(f"--- Historial de Chat para la sesión: {session_id} ---")
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
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recuperar el historial de chat de una sesión específica.")
    parser.add_argument("--session_id", required=True, help="El ID de la sesión para la cual recuperar el historial.")
    args = parser.parse_args()
    get_chat_history(args.session_id)
```

### `db_inspector.py`

Este script se conecta a la base de datos y puede listar todas las colecciones o inspeccionar el contenido de una colección específica.

```python
import os
import pymongo
from dotenv import load_dotenv
import json
import argparse

# Función para convertir ObjectId a string
def default_converter(o):
    if isinstance(o, pymongo.mongo_client.ObjectId):
        return str(o)
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ---
# Configuración
# ---
MONGO_URI = os.getenv("MONGO_URI")
MONGODB_DATABASE_NAME = "interactia_db"

# ---
# Script
# ---
def inspect_db(collection_name=None):
    if not MONGO_URI or "SU_CADENA_DE_CONEXION" in MONGO_URI:
        print("Error: La variable de entorno MONGO_URI no está configurada o es inválida.")
        return

    try:
        print(f"Conectando a MongoDB...")
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[MONGODB_DATABASE_NAME]
        print("Conexión exitosa.")

        if collection_name:
            print(f"Inspeccionando la colección '{collection_name}' en la base de datos '{MONGODB_DATABASE_NAME}'...")
            
            collection = db[collection_name]
            documentos = list(collection.find())
            
            if not documentos:
                print(f"No se encontraron documentos en la colección '{collection_name}'.")
            else:
                print(f"\n--- Contenido de la Colección: {collection_name} ---")
                for doc in documentos:
                    print(json.dumps(doc, indent=4, default=str))
                    print("---")
                print(f"--- Fin del Contenido ({len(documentos)} documentos) ---")
        else:
            print(f"Listando todas las colecciones en la base de datos '{MONGODB_DATABASE_NAME}'...")
            collections = db.list_collection_names()
            if not collections:
                print("No se encontraron colecciones.")
            else:
                print("Colecciones encontradas:")
                for name in collections:
                    print(f"- {name}")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error de conexión a MongoDB: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspeccionar la base de datos de MongoDB.")
    parser.add_argument("--collection", help="Nombre de la colección a inspeccionar.")
    args = parser.parse_args()
    inspect_db(args.collection)
```

### `get_latest_session_info.py`

Este script automatiza el proceso de depuración al consolidar la información de la sesión más reciente. Extrae automáticamente el ID de la última sesión del archivo `interactia_debug.log`, y luego recupera y muestra tanto el historial de chat de MongoDB como los registros de log correspondientes a esa sesión.

**Flujo de trabajo:**
1.  Lee `interactia_debug.log` para encontrar el `session_id` más reciente.
2.  Se conecta a MongoDB para obtener el historial de chat de esa sesión.
3.  Filtra y muestra los logs de `interactia_debug.log` que pertenecen a esa sesión.
4.  Presenta una vista combinada del chat y los logs para un análisis completo.

```python
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