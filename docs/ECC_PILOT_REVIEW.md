# Evaluacion tecnica: ECC en My Agent Skill Hub (piloto)
Fecha: 2026-11-22. Estado: **propuesta en rama**, no desplegado, no instalado globalmente.

## Fuente y trazabilidad
- Upstream: https://github.com/affaan-m/ECC
- Commit fijado: `4adeee6732a12d1540f49a4d50a38ce8c97f9a53` (la base revisada el 2026-11-22).
- Licencia de los materiales copiados: MIT, en `experiments/ecc/UPSTREAM_LICENSE`.
- El repositorio ECC tiene una superficie extensa de agentes, skills, hooks, reglas, scripts e instaladores. Este piloto NO es un fork completo.
- Revisión: lectura de README, install.ps1, hooks/README.md, LICENSE y skills seleccionadas; **no equivale a auditoría de seguridad de todo el código ni de sus dependencias**.

## Hallazgos y decisiones
| Aspecto | Hallazgo verificable | Decision |
|---|---|---|
| Funciones | ECC incluye skills, agentes, reglas, hooks y setup de Claude/Codex | Importar solo 4 skills como referencias |
| Instalador Windows | `install.ps1` verifica Node >=18, usa `npm install --ignore-scripts` si faltan dependencias y delega al instalador Node | NO ejecutar ni importar instalador |
| Hooks | Upstream registra acciones PreToolUse, PostToolUse, Stop, SessionStart y PreCompact; algunos pueden bloquear, formatear o realizar análisis | NO habilitar hooks ni el plugin |
| Tokens | Skills disponibles pueden añadir metadatos al contexto; invocarlas requiere leer contenido. Subagentes y hooks pueden aumentar llamadas | Wrappers breves; leer original a demanda; un agente |
| Seguridad | Materiales upstream muestran ejemplos de SQL, Compose, secretos de desarrollo y comandos operativos | Solo documentos como referencia, nunca ejecutar automáticamente |
| Duplicidad | El hub ya tiene `token-budget`, `sre-operations`, `incident-analysis`, `test-and-verify` | Mantenerlos como políticas superiores; no duplicar agentes |
| Datos de salud | Un repositorio público y prompts no son lugar para datos reales de pacientes ni registros con PHI | Solo datos ficticios o agregados aprobados |
| Versionado | ECC cambia con frecuencia | Fijar SHA y revisar cambios antes de actualizar |

## Material importado y alcance
- `ecc-postgres-patterns`: índices, consultas, seguridad, ajustes PostgreSQL. El material original incluye SQL de configuración: **no ejecutarlo sin revisión y aprobación**.
- `ecc-docker-patterns`: Compose, seguridad, volúmenes y red; contiene ejemplos específicamente diseñados para el propio instalador ECC que pueden no aplicar a SmartLab.
- `ecc-search-first`: comparar bibliotecas/soluciones antes de desarrollar. El original recomienda un agente researcher en modo completo; el wrapper **lo desactiva por defecto**.
- `ecc-strategic-compact`: checkpoints y compactación manual de sesiones largas. **No está instalado su script de hook**, por lo que no se realizarán compactaciones automáticas.

Fuentes originales completas están en `experiments/ecc/upstream/`; sus cuatro wrappers son skills reales registradas para Claude Code y Codex. Todas viven SOLO en esta rama hasta fusionar el PR.

## Casos de prueba seguros
1. **PostgreSQL**: optimizar una SELECT en base sintética con plan EXPLAIN generado previamente; comparar seguridad, calidad de índices y total de tokens.
2. **Docker**: examinar un docker-compose.yaml de ejemplo sin credenciales, proponer cambios como diff, nunca reiniciar contenedores.
3. **CIRA/ML**: aplicar la metodologia del hub para leakage, drift, reproducibilidad y QA; este piloto aun NO importa la skill completa de MLE.
4. **Investigacion**: comparar dos alternativas open source antes de crear una utilidad; modo rápido sin subagentes.
5. **Contexto**: sesión larga artificial con checkpoint manual y comparación de coste por respuesta correcta.

## Protocolo A/B reproducible
- Misma version de Claude, misma tarea, mismo repositorio y datos sintéticos, contextos nuevos equivalentes; repetir al menos 3 veces cada modo.
- A: `main` sin skills ECC. B: rama experimental, invocar solo la skill ECC específica.
- Registrar: modelo, fecha, tokens de entrada y salida **si están expuestos**, total de llamadas, duración, tests, calidad, errores, archivos consultados y cambios propuestos.
- No interpretar el contador de `/usage` de suscripción como coste monetario por solicitud; para ello se requieren métricas de uso adecuadas y condiciones de facturación.
- Archivo para capturar resultados: `experiments/ecc/benchmark-template.csv`. Dejar valores sin medir en blanco, no fabricar porcentajes.
- Éxito: mismo o mejor resultado técnico, sin eventos de seguridad ni agentes no solicitados; relación de tokens por resultado verificado no mayor que baseline, o justificar el exceso por la mejora.
- Descarga segura: no habilitar fuentes nuevas ni MCP sin revisar permisos; no subir credenciales, logs reales ni PHI.

## Verificación local en Windows (no ejecutada desde ChatGPT)
```powershell
git fetch origin
git switch experiment/ecc-selective-pilot-20261122
python scripts/hub.py validate
python -m unittest discover -s tests -v
```
Abrir Claude Code **dentro de esta carpeta** (no instalar ECC globalmente), verificar skills disponibles y usar `/context` y `/usage` cuando existan. No ejecutar `install.ps1`, `npx ecc-universal`, ni `/plugin install ecc@ecc` para este piloto.

## Limitaciones
- Lectura y análisis de código fuente/configuración: **parcial**, no pentest ni revisión exhaustiva de ~6.700 rutas.
- Skills importadas y documentación no equivalen a prueba real de ahorro de tokens o mejora de exactitud; resultados A/B **pendientes**.
- `python scripts/hub.py validate` y tests de Python deberán ejecutarse en CI o equipo local. No se han ejecutado aquí contra tu repositorio.
- Rollback: no fusionar PR; si se fusiona, revertir commit, retirar 4 registros y 4 skills en cada runtime manteniendo la bitácora.
