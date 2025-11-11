# Plan de Desarrollo de InteractIA

## Módulo de Verificación de Acciones (Fase 1 - Completada)

- [x] Crear un módulo de verificación de acciones (`verificador.py`).
- [x] Implementar verificación específica para la acción `clic` usando SSI.
- [x] Implementar verificación específica para la acción `escribir` usando la posición del cursor y OCR.
- [x] Integrar el nuevo módulo de verificación en el `Agente`.
- [x] Actualizar `requirements.txt` con las nuevas dependencias.

## Módulo de Verificación de Acciones (Fase 2 - LLM-Guided)

- [ ] **Modificar el formato de salida del LLM:**
    - [ ] Actualizar `MASTER_PROMPT_TEMPLATE` en `agente.py` para que el LLM genere un campo `expected_outcome` con la descripción del resultado esperado.
- [ ] **Actualizar la lógica del Agente:**
    - [ ] Modificar `_run_single_cycle` en `agente.py` para extraer y pasar `expected_outcome` al método de verificación.
- [ ] **Mejorar el Módulo Verificador:**
    - [ ] Modificar `verificar_accion` en `verificador.py` para que acepte el `expected_outcome`.
    - [ ] Crear un nuevo método de verificación genérico que use un modelo de visión para comparar la captura de pantalla con la descripción del `expected_outcome`.
    - [ ] Reemplazar la lógica de verificación actual (basada in SSI y OCR) con la nueva verificación guiada por LLM.
- [ ] **Actualizar `vision.py` (si es necesario):**
    - [ ] Crear una nueva función `verify_image_with_description` para encapsular la lógica de comparación entre imagen y descripción.

## Próximos Pasos

- [ ] Implementar una estrategia de reintento para acciones fallidas.
- [ ] Desarrollar un sistema de "deshacer" para revertir acciones.
- [ ] Añadir más acciones compuestas (e.g., `abrir_aplicacion`, `cerrar_ventana`).
- [ ] Mejorar el sistema de aprendizaje para que las lecciones sean más efectivas.