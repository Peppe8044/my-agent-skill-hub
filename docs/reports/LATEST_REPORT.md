Copia de PHASE_03_REPORT.md

# Reporte de fase 03: Integración de capacidades externas y control de tokens

Documento sintético generado de forma determinista. No incluye registros completos.

## 1. Número de fase y objetivo

Fase 3: Integración de capacidades externas y control de tokens

Objetivo: Inventariar de forma determinista los 8 submódulos, aprobar por reglas las capacidades compatibles, instalarlas automáticamente con carga bajo demanda, procedencia y rollback, e incorporar reglas de control de tokens.

## 2. Resumen ejecutivo

- PR #2 fusionado (97aedfa); rama feat/external-skills-integration.
- Escáner determinista: 2.204 skills y 312 agentes clasificados sin LLM.
- 995 skills aprobadas (14 activas y 981 en catálogo bajo demanda), 181 requieren revisión de scripts y 1.028 rechazadas; 45 agentes en catálogo.
- install/new/bootstrap instalan automáticamente lo aprobado, con procedencia, copias de seguridad y rollback.
- Esfuerzo medium para ejecutores; launch fuerza --effort high porque la configuración global xhigh prevalecía.

## 3. Estado inicial y estado final

**Estado inicial:**
- registry/integrations.json sin skills aprobadas.
- Ninguna capacidad externa instalable.

**Estado final:**
- Registro central de aprobados con commit fijado y sha256.
- Catálogo bajo demanda y skill propia skill-catalog.
- PR #3 con CI success.

## 4. Componentes implementados

- scripts/external_scan.py
- registry/external_capabilities.json
- registry/EXTERNAL_SKILLS_INVENTORY.json
- Instalación por niveles (activo/catálogo)
- templates/agent-hub/catalog.py
- hub.py rollback
- skill skill-catalog
- Reglas de esfuerzo y tokens

## 5. Archivos creados y modificados

Creados:
- scripts/external_scan.py
- scripts/smoke_bootstrap.py
- templates/agent-hub/catalog.py
- skills/skill-catalog/SKILL.md
- tests/test_external_scan.py
- tests/test_external_install.py
- docs/EXTERNAL_SKILLS_REPORT.md
- docs/SKILL_COMPATIBILITY_REPORT.md
- docs/LICENSE_REGISTRY.md
- docs/TOKEN_USAGE_REPORT.md
- docs/decisions/0005-external-capabilities.md

Modificados:
- scripts/project_install.py
- scripts/hub.py
- scripts/bootstrap.py
- scripts/doctor.py
- scripts/model_policy.py
- .claude/hooks/model_guard.py
- .claude/agents/* (effort)
- MODEL_POLICY.json
- AGENTS.md
- README.md

## 6. Versiones y dependencias

- Submódulos sin cambios de commit fijado
- Claude Code 2.1.332

## 7. Comandos relevantes ejecutados

- `python scripts/hub.py external-scan / --check`: salidas deterministas sin desviaciones
- `python -m unittest discover -s tests`: 93 tests OK
- `python scripts/smoke_bootstrap.py <temporal>`: ok: true
- `claude -p en el proyecto temporal`: 57 skills detectadas, 0 del catálogo en contexto

## 8. Resultados reales de pruebas

| Prueba | Estado | Evidencia |
|---|---|---|
| unittest | ✅ pasó | 93 OK; commits verificados por separado (74 y 93) |
| Bootstrap end-to-end | ✅ pasó | 30/43 propios, 14 activas, 981+45 catálogo, 0 duplicados, segunda instalación sin cambios |
| Detección en Claude Code | ✅ pasó | init con 57 skills del proyecto y 0 del catálogo |
| Carga individual bajo demanda | ✅ pasó | Skill(godot-patterns) y catalog.py search → show → lectura de una sola skill |
| model_guard (opus y effort xhigh) | ✅ pasó | ambas llamadas bloqueadas |
| Esfuerzo de subagentes | ✅ pasó | transcripción: effort medium |
| GitHub Actions | ✅ pasó | run 46106738993 success |
| Revisión humana de 181 skills con scripts y 45 agentes | ⏳ pendiente | fuera del alcance automático |

## 9. Evidencia de funcionamiento

- Las reglas R1–R9 y la R6b están documentadas en SKILL_COMPATIBILITY_REPORT.
- La clasificación automatizada no es una auditoría de seguridad completa.

## 10. Riesgos y hallazgos de seguridad

- El contenido aprobado no se revisó manualmente línea por línea.
- Instalación completa de alrededor de 1 minuto por hashes y git status.
- Configuración global effortLevel xhigh.

## 11. Decisiones técnicas y justificación

- Dos niveles: 14 activas + catálogo bajo demanda: Cientos de skills activas inflarían el contexto de cada sesión.
- R6b y dominio por defecto por repositorio: Corrigen 10 falsos positivos defensivos y 227 rechazos por falta de palabras clave.
- Excluir harnesses/orquestadores del nivel activo: Competirían con la política de un único orquestador Opus.
- launch pasa --effort: La configuración global xhigh prevalecía sobre el frontmatter (verificado).

## 12. Consumo de tokens por agente y modelo

| Agente | Modelo | Tokens | Llamadas a herramientas | Duración (s) | Fuente |
|---|---|---|---|---|---|
| S1 escáner | claude-sonnet-5-5 (effort medium) | 104504 | 12 | 447.5 | task-notification |
| S2 instalador, catálogo y rollback | claude-sonnet-5-5 (effort medium) | 171926 | 61 | 2409.5 | task-notification |
| S3 reglas, effort y documentación | claude-haiku-5-5 (effort medium) | 85622 | 19 | 259.5 | task-notification |
| **Total** |  | 362052 | 92 | 3116.5 |  |

## 13. Costos medidos

- Detección en Claude Code: USD 0.45 (fuente: total_cost_usd)
- Verificación de --effort high: USD 0.28 (fuente: total_cost_usd)

## 14. Duración de la fase

No medida con precisión; el ejecutor más largo (S2) tardó 40 min.

## 15. Problemas encontrados y soluciones

- Falsos positivos del filtro de seguridad ofensiva: Regla R6b basada en la intención del nombre.
- catalog.py enable no validaba nombres ni rutas: Validación añadida, con prueba.
- Un heredoc de S3 quedó bloqueado: Proceso detenido; la edición era idempotente.
- La documentación trataba AGPL como prohibición: Corregido al cerrar la fase: excluded-by-policy.

## 16. Componentes pendientes

- Revisión humana de las skills con scripts y de los agentes de catálogo.
- Agent Memory y OpenViking (restricción vigente).
- Hooks de ECC (fase 4).

## 17. Decisiones que requieren autorización

- Fusionar el PR #3
- Bajar effortLevel global a high

## 18. Commits, Pull Requests y enlaces

**Commits:**
- c31a46e escáner y registro
- c9fe900 instalación por niveles, catálogo, rollback y effort
- 7de9fdd documentación e informes
- 4824f88 aclaración AGPL y alcance de la clasificación

**Pull Requests:**
- #3 fusionado como 623b3ca

**Enlaces:**
- https://github.com/Peppe8044/my-agent-skill-hub/pull/3

## 19. Recomendación para la siguiente fase

Integrar los hooks de ECC de forma selectiva con un gestor de hooks propio e implantar informes consolidados por fase.
