# ADR-0005: Capacidades externas con aprobación por reglas y catálogo bajo demanda

- Estado: Aceptada
- Fecha: 2026-11-28
- Contexto: El inventario de `external/` contiene 2.204 archivos SKILL.md (incluidas traducciones y ports) y 312 archivos de agentes, además de hooks y servidores MCP. Listar cientos de skills en cada sesión consume contexto; activar todo degrada la selección de skills propias. Hooks, MCP y servicios no pueden aprobarse en bloque.
- Opciones: (A) instalar todo como activo; (B) selección manual por proyecto; (C) aprobación por reglas con un nivel activo pequeño y un catálogo bajo demanda.
- Decisión: C.
- Consecuencias: solo entra contenido aprobado por reglas; las skills que dependen de código requieren revisión humana; los agentes externos nunca se activan automáticamente (solo `sonnet` o `haiku`, y solo si se habilitan); las licencias se copian junto al contenido; los cambios son reversibles con `rollback`; hooks, MCP, plugins y servicios quedan fuera.
- Evidencia: docs/EXTERNAL_SKILLS_REPORT.md y docs/SKILL_COMPATIBILITY_REPORT.md.
- Revisión: tras la primera ejecución de `external-scan` con conteos medidos y tras medir el consumo real de contexto del nivel activo.
