# Plan de Desarrollo - Agente InteractIA

## 1. Implementar el Orquestador de Acciones en `agente.py`

**Objetivo:** Permitir que el agente interprete y ejecute acciones de alto nivel o compuestas, traduciéndolas en secuencias de acciones primitivas que `controlador.py` pueda manejar.

**Pasos:**
1.  **Añadir `_ejecutar_accion_compuesta`:** Crear un nuevo método en la clase `Agente` para manejar la lógica de las acciones compuestas.
2.  **Modificar `stream_run`:** Ajustar el bucle principal para que intente ejecutar las acciones a través de `_ejecutar_accion_compuesta` antes de recurrir a `_ejecutar_accion_primitiva`.
3.  **Definir Acciones Compuestas Iniciales:** Implementar la lógica para algunas acciones compuestas básicas (ej. `navegar_a_url`, `buscar_en_google`) dentro de `_ejecutar_accion_compuesta`.
4.  **Actualizar `_construir_prompt`:** Informar al modelo de IA sobre la existencia y el formato de estas nuevas acciones compuestas en el prompt.

**Estado:** Completado y verificado. Se ha implementado el método `_ejecutar_accion_compuesta`, se ha integrado en `stream_run` y se ha actualizado `_construir_prompt` con las nuevas acciones compuestas.