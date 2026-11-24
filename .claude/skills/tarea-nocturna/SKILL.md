---
name: tarea-nocturna
description: Procedimiento de cada corrida del agente desarrollador (cada 7 horas). Toma el próximo ítem de BACKLOG.md, lo entrega con spec → tests → código, lo hace revisar por el agente `companero` y lo integra a `desarrollo` solo si el compañero aprueba. Usar en cada corrida programada o cuando se pida "avanzar con el backlog".
---

# Tarea programada: desarrollador + compañero revisor

Trabajás sin nadie a quien preguntar. Sos el **desarrollador**. El agente `companero` es tu revisor: conoce
las clases y la consigna, y sin su `APROBADO` nada entra a `desarrollo`. Flora mira el resultado cada
7 horas y es la única que integra `desarrollo` a `main` (ADR-0010).

Donde normalmente harías la entrevista, decidí lo más razonable y dejalo escrito en "Supuestos" de la spec.

## 0. Arrancar
- `git fetch origin && git checkout desarrollo && git pull`.
- Leé `docs/feedback-flora.md`. **Lo que pide ahí va primero**, antes que el backlog: si pide cambios
  sobre algo ya integrado, eso es la tarea de esta corrida (con el mismo ciclo). Al resolver un pedido,
  marcalo `[x]` en ese archivo con la rama donde quedó; no borres lo que escribió Flora.
- Leé `AGENTS.md`, las últimas entradas de `CHANGELOG.md`, la última revisión en `docs/revisiones/` y
  los ADRs que nombre el ítem.
- Si la corrida anterior dejó un ítem en `[~]` sin integrar (el compañero pidió cambios y se agotaron las
  rondas), retomalo desde su rama en vez de empezar uno nuevo.
- Si no, tomá el primer ítem `[ ]` de `BACKLOG.md`. Rama: `noche/AAAA-MM-DD-NNN` desde `desarrollo`.

## 1. Spec
Copiá `docs/specs/TEMPLATE.md` a `docs/specs/NNN-nombre.md`. "Cómo se verifica" lista cada test por
nombre y qué comportamiento prueba, incluidos los casos que deben fallar. Commit: `spec: NNN …`.

## 2. Tests primero
Escribí los tests y confirmá que fallan por la razón correcta (no por un import roto). Un test es
significativo si fallaría con una implementación trivial. Al menos un caso borde por regla.
Commit: `tests: NNN …`.

## 3. Código
Lo mínimo para que pasen, respetando los ADRs. `make check` en verde. No toques tests de ítems
anteriores. Lógica crítica (verificador, tools, métricas): `make mutation MODULO=<archivo>`; con
sobrevivientes, agregá tests hasta ≥ 80% o explicá por qué el mutante es equivalente.
Commits chicos (`feat: …`, `fix: …`).

## 4. Registro (obligatorio en todo cambio)
- `CHANGELOG.md`: entrada nueva arriba de todo (`## AAAA-MM-DD · rama · …`).
- **ADR nuevo siempre** en `docs/adr/NNNN-titulo.md` (siguiente número libre, formato de
  `docs/adr/0000-template.md`, estado `Propuesto`): qué decidiste en este cambio, qué alternativas
  descartaste y cómo se verifica. Si no hubo decisión de arquitectura, registrá las decisiones de diseño.
- `BACKLOG.md` (ítem a `[~]` con la rama) y el reporte en `docs/noches/AAAA-MM-DD-HHMM.md`.
- `make registro` en verde antes de pedir revisión. Commit y push: `git push -u origin <rama>`.
- Si el compañero pide cambios, cada ronda de arreglos agrega su línea en la misma entrada del CHANGELOG.

## 5. Revisión del compañero (máximo 3 rondas)
1. Llamá al agente `companero` (herramienta Agent, `subagent_type: "companero"`) con: rama de la tarea,
   base `desarrollo`, número de ítem y la ruta del reporte. No le expliques por qué está bien: que lo
   verifique él.
2. Guardá su respuesta **tal cual, sin editarla** en `docs/revisiones/NNN-ronda-K.md` (archivo nuevo por
   ronda; un hook impide modificar revisiones ya escritas) y commitealo: `revision: NNN ronda K (<veredicto>)`.
3. Según el veredicto:
   - `APROBADO` → paso 6.
   - `CAMBIOS` → resolvé cada hallazgo bloqueante e importante con commits `fix: …`; los menores, si son
     baratos. Si no estás de acuerdo con un hallazgo, no lo ignores: respondé en el reporte por qué. Push y
     volvé a 5.1 (ronda K+1).
   - `ESCALAR A FLORA` → anotá la decisión pendiente arriba de todo en `docs/feedback-flora.md` bajo
     "Decisiones pendientes", marcá el ítem `[!]` y terminá sin integrar.
4. Si después de la ronda 3 no hay `APROBADO`: no integres. Ítem `[!]`, push de la rama y explicá en el
   reporte qué quedó sin resolver. La próxima corrida lo retoma.

## 6. Integrar a `desarrollo`
```
git checkout desarrollo && git pull
git merge --no-ff <rama> -m "merge: NNN <título> (aprobado por companero, ronda K)"
make check
git push origin desarrollo
```
Si el merge tiene conflictos o `make check` falla después del merge, abortá (`git merge --abort` o
`git reset --hard origin/desarrollo`), dejá el ítem en `[~]` y explicalo en el reporte. Nunca pushees a
`main` ni hagas `--force`.

Una corrida = un ítem. Si terminaste y sobra mucho tiempo, no arranques otro: la cadencia la marca la
tarea programada, para que Flora pueda seguirle el ritmo.

## Reporte de la corrida (`docs/noches/AAAA-MM-DD-HHMM.md`)
```
## Qué hace
## Cómo se verificó
- make check: <resultado>
- make registro: <resultado>
- mutation: <módulo> <muertos>/<total>
- tests existentes modificados: <salida de make tests-modificados>
- revisión del compañero: <veredicto final> en <K> rondas (docs/revisiones/NNN-ronda-*.md)
## Supuestos y decisiones
## Hallazgos del compañero que no se resolvieron (y por qué)
## Para la defensa
- Qué hace cada pieza nueva, en dos líneas.
- Por qué se hizo así (con el ADR que corresponda) y qué alternativa se descartó.
- Una pregunta que podría hacer la cátedra y cómo responderla.
## Qué tiene que mirar Flora
```

## Si te trabás
No inventes alcance ni bajes la vara de los tests. Commiteá lo que tengas en la rama, marcá el ítem `[!]`,
escribí en el reporte qué falta y qué necesitarías, y anotalo en `docs/feedback-flora.md` como decisión
pendiente si depende de ella.
