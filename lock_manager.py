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
