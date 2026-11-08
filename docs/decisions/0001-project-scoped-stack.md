# ADR-0001: Stack evaluado por proyecto

- Estado: Aceptada como política inicial
- Fecha: 2026-11-08
- Contexto: Un stack fijo acelera algunos proyectos pero introduce dependencias superfluas en otros.
- Opciones: (A) stack TypeScript universal; (B) stack decidido en cada proyecto; (C) libertad sin guía.
- Decisión: B, evaluando A y otras alternativas con un baseline simple según requisitos.
- Consecuencias: una pequeña evaluación inicial extra; reducción esperada de sobreingeniería, por verificar.
- Evidencia: docs/DECISION_GUIDE.md; patrones de framework y SDK documentados en docs/SOURCES.md.
- Revisión: cuando existan tres proyectos evaluados con tiempos/calidad reales.