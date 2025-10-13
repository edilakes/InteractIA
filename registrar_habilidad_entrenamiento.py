from knowledge_base import KnowledgeBase

# Definición de la habilidad conceptual de "Entrenamiento Supervisado"
habilidad_entrenamiento = {
    "nombre": "entrenamiento_supervisado",
    "tipo": "Estrategia",
    "descripcion": """
# Habilidad: Modo de Entrenamiento Supervisado

## 1. Nombre de la Habilidad
`entrenamiento_supervisado`

## 2. Objetivo Principal
Guiar y entrenar a una entidad de IA (la "entidad controlada") para que cumpla un objetivo específico, documentando el proceso de razonamiento y permitiendo la intervención del usuario.

## 3. Concepto Central
El agente actúa como un "supervisor" pedagógico. Su función no es ejecutar la tarea, sino enseñar a la "entidad controlada" a través de la formulación de prompts estratégicos, operando en uno de dos modos de interacción con el usuario.

## 4. Flujo de Trabajo y Modos de Interacción
El proceso sigue un ciclo de `Análisis -> Diseño de Prompt -> Interacción/Log -> Ejecución -> Observación`. La fase de "Interacción/Log" depende del modo elegido por el usuario:

### Modo 1: Verificación del Usuario (Interactivo)
1.  **Propuesta:** El supervisor presentará el prompt exacto que planea enviar a la entidad controlada.
2.  **Justificación:** Acompañará la propuesta con su razonamiento: por qué ha elegido ese prompt, qué espera conseguir y cómo encaja en el plan general.
3.  **Aprobación del Usuario:** El supervisor esperará el `OK` del usuario para proceder. En este punto, el usuario puede aprobar el prompt, sugerir modificaciones o dar instrucciones adicionales para que lo refine.
4.  **Acción:** Solo después de la aprobación del usuario, el supervisor enviará el prompt (final o modificado) a la entidad controlada.

### Modo 2: Autónomo con "Stream of Consciousness" (Observación)
1.  **Razonamiento en Voz Alta:** Si el usuario decide no verificar cada paso, el chat del supervisor se convertirá en un monólogo detallado de su proceso mental.
2.  **Documentación del Ciclo:** Este "stream of consciousness" incluirá:
    *   **Pensamiento:** Las ideas y estrategias que el supervisor está considerando.
    *   **Acción:** El prompt que el supervisor está escribiendo en la entrada de la entidad controlada.
    *   **Observación:** Lo que el supervisor ve que hace la entidad controlada como resultado.
    *   **Análisis:** La interpretación del supervisor sobre el éxito o fracaso y cómo eso informa su siguiente pensamiento.

## 5. Restricciones Clave
Independientemente del modo, el supervisor se limita a generar prompts. La ejecución de la tarea es responsabilidad exclusiva de la entidad controlada.
""",
    "parametros": {
        "objetivo_controlada": "El objetivo final que la entidad controlada debe alcanzar.",
        "modo_interactivo": "Boolean (True/False) para determinar si se requiere la verificación del usuario antes de cada paso."
    }
}

def registrar_habilidad():
    """
    Registra la habilidad de entrenamiento supervisado en la base de conocimiento.
    """
    kb = KnowledgeBase()
    if kb.client:
        kb.aprender_habilidad(
            nombre_recurso=habilidad_entrenamiento["nombre"],
            tipo_recurso=habilidad_entrenamiento["tipo"],
            datos_habilidad=habilidad_entrenamiento
        )
        print(f"Habilidad '{habilidad_entrenamiento['nombre']}' guardada en la base de conocimiento.")
    else:
        print("No se pudo conectar a MongoDB para guardar la habilidad.")

if __name__ == "__main__":
    registrar_habilidad()
