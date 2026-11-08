# Selección de tecnología por proyecto

No existe stack universal. El análisis sigue esta secuencia:
1. Clasifica producto (web, API, ML, pipeline, CLI, integración, móvil, SRE) y necesidades no funcionales (seguridad, datos, escalabilidad, latencia, offline, operación, equipo).
2. Identifica qué **NO** hace falta. Baseline: solución más pequeña que resuelve la necesidad sin comprometer seguridad.
3. Compara al menos dos alternativas con criterios explícitos: ajuste funcional (30%), conocimiento del equipo (20%), mantenimiento/ecosistema (20%), operación/despliegue (15%), seguridad/regulación (10%), costo (5%). Pesos ilustrativos, adaptables al contexto.
4. Elabora pruebas técnicas específicas para incertidumbres importantes (spike, PoC, benchmarking real).
5. Documenta decisión y contraindicaciones. Aprobación humana ante riesgos no triviales.

## Perfiles orientativos
- Web fullstack: TypeScript + React + backend Hono/Express/Fastify según restricciones; PostgreSQL y Drizzle solo si hacen falta.
- API Python: FastAPI o framework apropiado; base de datos solo si persiste estado.
- Ciencia de datos: Python, pandas/Polars, scikit-learn; MLflow solo si necesita ciclo de experimentos.
- SRE/automatización: Bash/Python y herramientas ya instaladas; priorizar observabilidad y rollback.
- Producto multiagente: un agente + herramientas primero; orquestación duradera solo si existe trabajo dependiente/con estado.

Justificar siempre por qué no usar opciones más complejas.