# ADR-0006: Agent Memory como componente reutilizable, local y aislado por proyecto

- Estado: Aceptada (pendiente de verificación MCP por el orquestador)
- Fecha: 2026-11-28
- Contexto: se necesita memoria persistente entre sesiones sin APIs de pago, sin mezclar proyectos y sin tocar la configuración global del usuario. `rohitg00/agentmemory` (submódulo `external/agentmemory`, commit 5c9e2e6) ofrece un servicio REST + servidor MCP; su CLI descarga el motor `iii` a `~/.agentmemory/bin` y guarda el secreto en `~/.agentmemory` salvo que se redirijan.
- Opciones: (A) instancia global única; (B) `--instance N` del propio CLI; (C) una instancia por proyecto con directorio de datos y HOME propios, puerto registrado por proyecto.
- Decisión: C.
  - Datos en `<proyecto>/.agent-hub/memory/{data,home}` (ignorado por git); `config.json` registra host `127.0.0.1` y puerto (3200 + hash(ruta)%100 * 10, saltando puertos ocupados; REST N, visor N+2, motor N+46023).
  - Variables usadas: `AGENTMEMORY_DATA_DIR`, `AGENTMEMORY_ENV_FILE`, `AGENTMEMORY_TOOLS=core`, `AGENTMEMORY_AUTO_COMPRESS=false`, `AGENTMEMORY_INJECT_CONTEXT=false`, `AGENTMEMORY_URL`; `USERPROFILE`/`HOME` redirigidos a `.agent-hub/memory/home` para que el motor `iii` (~6 MB) y el secreto no se instalen en el HOME real. Se eliminan del entorno las claves de proveedores (sin LLM, sin compresión por LLM).
  - Embeddings locales: desactivados. El código fijado los soporta (`EMBEDDING_PROVIDER=local`, `Xenova/all-MiniLM-L6-v2`) pero descargan el modelo en la primera petición y no se midió beneficio; el recall usa BM25.
  - Sin hooks de captura de agentmemory ni importación de conversaciones. Integración solo por MCP: entrada `agentmemory` en `.mcp.json` del proyecto (fusión idempotente, conserva otros servidores) que ejecuta `node external/agentmemory/dist/cli.mjs mcp` con `AGENTMEMORY_URL` y `AGENTMEMORY_DATA_DIR` (el secreto se lee de `data/secret`, nunca se escribe en `.mcp.json`). La entrada contiene rutas absolutas de la máquina.
  - Skills: las de `plugin/skills` documentan el plugin y sus hooks/REST; no se registran (ninguna compatible sin activar los hooks descartados).
  - Servicio: `python scripts/hub.py memory start|stop|status|recover|configure --target <dir>`. `stop` usa `agentmemory stop` oficial (reapa el demonio Compose) y luego termina los PID que escuchan; `recover` = stop + borrar pid/lock obsoletos + start. `bootstrap` y `update` solo configuran; nunca arrancan el servicio.
  - Dependencias (una vez, en el checkout fijado; `node_modules`/`dist` fuera de git): `cd external/agentmemory && npm install --ignore-scripts && npm run build`.
- Consecuencias: el primer arranque por proyecto descarga el motor (red) a su carpeta; el build modifica archivos rastreados de `plugin/scripts` del submódulo (cambio de formato, a restaurar con `git -C external/agentmemory checkout -- .`); las rutas absolutas en `.mcp.json` impiden compartirlo entre máquinas sin regenerarlo con `update`.
- Revisión: tras la comprobación MCP real con Claude Code y si se pide búsqueda semántica (medir beneficio antes de activar embeddings).
