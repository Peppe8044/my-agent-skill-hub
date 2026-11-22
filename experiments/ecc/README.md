# Piloto ECC de bajo consumo
Este directorio conserva **cuatro archivos originales** de `affaan-m/ECC`, fijados al commit `4adeee6732a12d1540f49a4d50a38ce8c97f9a53`. No contiene el instalador completo.

## Activación
Las skills usables en el hub son `ecc-postgres-patterns`, `ecc-docker-patterns`, `ecc-search-first` y `ecc-strategic-compact` en `skills/`, `.claude/skills/` y `.agents/skills/`. Los archivos de `upstream/` son *referencias*, no hooks ni scripts.

Lee `docs/ECC_PILOT_REVIEW.md`. Las reglas de `AGENTS.md` prevalecen; un agente por defecto, solo QA/sandbox con datos sintéticos. No activar ECC global, no copiar `hooks/hooks.json`, no ejecutar instaladores, no acceder a producción. La integración solo está disponible en la rama de prueba hasta un merge explícito.

## Medición
Rellena `benchmark-template.csv` para comparar las mismas tareas en `main` y la rama experimental. Evitar resultados falsos: campos sin medir se dejan vacíos. Guardar evidencia sanitizada, sin PHI/PII.

## Atribución
Copyright (c) 2026 Affaan Mustafa. Material original bajo MIT: `UPSTREAM_LICENSE`. Los wrappers son una adaptación local para este hub.
