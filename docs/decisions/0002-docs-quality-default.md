# ADR-0002: Documentación y pruebas como gates por defecto

- Estado: Aceptada como política inicial
- Fecha: 2026-11-08
- Contexto: La documentación omitida y las pruebas no registradas producen retrabajo y falta de trazabilidad.
- Opciones: (A) confiar en instrucciones; (B) instrucciones + checks locales + CI + revisión humana.
- Decisión: B. Exigir WORK_LOG y CHANGELOG en PRs de cambios materiales, QA, revisión de seguridad y estado honesto.
- Consecuencias: overhead documental proporcional; se permite excepción de proceso explícita, registrada.
- Límite: controles CI no prueban calidad semántica ni reemplazan branch protection.