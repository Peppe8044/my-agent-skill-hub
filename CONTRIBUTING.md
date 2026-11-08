# Contribuir

1. Mantén instrucciones globales breves; procesos en skills bajo demanda.
2. Abre un cambio pequeño con problema, criterios de aceptación y stack justificado cuando proceda.
3. Si modificas una skill fuente en `skills/`, ejecuta `python scripts/hub.py sync` para publicar adaptadores.
4. Agrega pruebas y documenta comandos/resultados reales.
5. Actualiza `docs/WORK_LOG.md` siempre que el cambio sea material y `docs/CHANGELOG.md` si es visible/funcional.
6. Ejecuta `python scripts/hub.py validate` y `python -m unittest discover -s tests -v`.
7. Revisa seguridad, dependencias y permisos; no uses información de clientes.
8. Envía PR utilizando el checklist y revisión de CODEOWNERS si la regla GitHub está habilitada.

Las excepciones de proceso solo aplican si el owner las aprueba expresamente y constan en `docs/EXCEPTIONS.md` con compensaciones.