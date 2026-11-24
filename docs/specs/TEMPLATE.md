# Spec NNN: título

**Ítem del backlog:** NNN · **Rama:** `noche/AAAA-MM-DD-NNN` · **ADRs relacionados:** ADR-XXXX

## Qué se va a hacer
Una o dos oraciones. Qué problema del PRD resuelve.

## Interfaz
Firmas públicas (funciones, clases, modelos Pydantic) con tipos de entrada y salida.

## Archivos a tocar
- Crear: …
- Modificar: …

## Fuera de alcance
Lo que explícitamente NO se hace en esta tarea (y archivos que no se tocan).

## Supuestos
Decisiones tomadas sin poder consultar. Cada una, con su justificación.

## Cómo se verifica
- Tests (nombre de cada test y qué comportamiento prueba; incluir casos borde y casos que deben fallar).
- Sensores: `make check`; `make mutation MODULO=…` si es lógica crítica (umbral: ≥ 80% de mutantes muertos).
- Qué tendría que revisar Flora a mano.
