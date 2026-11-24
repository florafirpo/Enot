---
name: tarea-nocturna
description: Procedimiento para tomar el próximo ítem de BACKLOG.md y entregarlo como PR siguiendo spec → tests → código. Usar en cada corrida nocturna o cuando se pida "avanzar con el backlog".
---

# Tarea nocturna (spec → tests → código → PR)

Trabajás sin nadie a quien preguntar. Donde normalmente harías la entrevista, decidí lo más razonable
y dejalo escrito en la sección "Supuestos" de la spec.

## 1. Orientarte (sin escribir nada todavía)
- Leé `AGENTS.md`, `CHANGELOG.md` (las últimas entradas) y los ADRs que nombra el ítem.
- En `BACKLOG.md`, tomá el primer ítem `[ ]`. Si depende de un ítem `[~]` (PR sin aprobar), creá tu rama
  desde la rama de ese PR y aclaralo en la descripción.
- Rama: `noche/AAAA-MM-DD-NNN` (fecha de hoy, número del ítem).

## 2. Spec
- Copiá `docs/specs/TEMPLATE.md` a `docs/specs/NNN-nombre.md` y completala. "Cómo se verifica" lista
  cada test por nombre y qué comportamiento prueba, incluidos los casos que deben fallar.
- Commit: `spec: NNN …`.

## 3. Tests primero
- Escribí los tests de la spec. Corrélos y confirmá que fallan por la razón correcta (no por un import roto).
- Un test es significativo si fallaría con una implementación trivial (que devuelve siempre lo mismo,
  o que ignora un parámetro). Pensá al menos un caso borde por regla.
- Commit: `tests: NNN …`.

## 4. Código
- Implementá lo mínimo para que los tests pasen, respetando los contratos de los ADRs.
- `make check` en verde. No toques tests de ítems anteriores; si uno está mal, explicalo en el PR.
- Si es lógica crítica (verificador, tools, métricas): `make mutation MODULO=<archivo>`. Si sobreviven
  mutantes, agregá tests hasta matar al menos el 80% o explicá por qué un mutante es equivalente.
- Commits chicos con mensajes claros (`feat: …`, `fix: …`).

## 5. Registro
- `CHANGELOG.md`: entrada nueva arriba de todo.
- ADR nuevo si decidiste algo de arquitectura que no estaba (dependencia nueva, cambio de contrato).
- `BACKLOG.md`: el ítem pasa a `[~]` con el número de PR o el nombre de la rama.
- `docs/noches/AAAA-MM-DD.md`: reporte breve (ver formato abajo).

## 6. Entregar
- `make tests-modificados` y pegá la salida en el PR.
- Push de la rama (`git push -u origin noche/…`) y PR contra `main` (con `gh pr create` si está
  disponible; si no, dejá el reporte y la descripción listos en `docs/noches/`).
- Nunca merges ni pushees a `main`.

## Descripción del PR (y del reporte de la noche)
```
## Qué hace
## Cómo se verificó
- make check: <resultado>
- mutation: <módulo> <muertos>/<total>
- tests existentes modificados: <salida de make tests-modificados>
## Supuestos y decisiones
## Para la defensa
- Qué hace cada pieza nueva, en dos líneas.
- Por qué se hizo así (con el ADR que corresponda) y qué alternativa se descartó.
- Una pregunta que podría hacer la cátedra y cómo responderla.
## Qué tiene que revisar Flora
```

## Si te trabás
No inventes alcance ni bajes la vara de los tests. Commiteá lo que tengas, abrí el PR como borrador,
marcá el ítem `[!]` y explicá qué falta y qué necesitarías.
