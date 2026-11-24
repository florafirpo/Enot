# Spec 001: Modelos de dominio y tools determinísticas

**Ítem del backlog:** 001 · **Rama:** `noche/2026-11-23-001` · **ADRs relacionados:** ADR-0003, ADR-0005

## Qué se va a hacer
Los tipos con los que trabaja el agente (bodega, perfil de viaje, itinerario) y las tres tools de cálculo
que no puede hacer el LLM: tiempo de traslado, si una bodega está abierta y costo de las experiencias.
Son la base del verificador (ítem 002) y del planificador (ítem 004).

## Interfaz

`enot/modelos.py`
- `Bodega` — `id, nombre, zona, comuna, lat: float | None, lon: float | None, horarios: list[Horario],
  experiencias: list[Experiencia], requiere_reserva, tiene_restaurante, opciones_sin_tacc,
  opciones_vegetarianas, opciones_veganas, accesible_movilidad_reducida, acepta_grupos,
  capacidad_max_grupo, idiomas, perfil, url_web, fuentes`. `Bodega.desde_ficha(dict) -> Bodega`
  convierte una línea de `fichas.jsonl` (con su `_meta`). `Horario` y `Experiencia` se reutilizan de
  `corpus/schema.py`.
- `PerfilViaje` — `cantidad_dias (1–3), dia_inicio: Dia, transporte ("auto" | "traslado" | "bici" | "a_pie"),
  personas (≥ 1), presupuesto_max_por_persona: float | None (EUR), restricciones_alimentarias
  (lista de "sin_tacc" | "vegetariano" | "vegano"), movilidad_reducida: bool, idiomas: list[str],
  zonas_preferidas: list[str], bodegas_evitar: list[str], preferencias: str | None,
  hora_inicio_jornada = "09:30", hora_fin_jornada = "18:30"`.
- `Parada` — `bodega_id, hora_inicio "HH:MM", duracion_min > 0, experiencia: str | None`.
- `DiaItinerario` — `numero ≥ 1, dia_semana: Dia, paradas: list[Parada]`.
- `Itinerario` — `dias: list[DiaItinerario], notas: str | None`.
- `a_minutos("HH:MM") -> int` y `a_hora(int) -> "HH:MM"`. Toda hora inválida se rechaza al validar.

`enot/corpus_local.py`
- `cargar_corpus(ruta = config.FICHAS_JSONL) -> dict[str, Bodega]`. Una línea inválida se saltea y se
  cuenta; no corta la carga.

`enot/tools/` (errores como valor, nunca excepciones hacia el loop)
- `tiempo_traslado(corpus, origen_id, destino_id, modo) -> ResultadoTraslado(minutos: int | None,
  km: float | None, error: str | None)`.
- `abierta_en(corpus, bodega_id, dia, hora_inicio, duracion_min) -> ResultadoHorario(abierta: bool | None,
  motivo: str)`. `None` = no se sabe (la bodega no publica horario).
- `costo_experiencias(corpus, items: list[ItemCosto], personas) -> ResultadoCosto(total_eur,
  detalle, sin_precio, errores)`. `ItemCosto(bodega_id, experiencia: str | None)`.

## Archivos a tocar
- Crear: `enot/modelos.py`, `enot/corpus_local.py`, `enot/tools/{__init__,distancias,horarios,costos}.py`,
  `tests/fixtures/fichas_sinteticas.jsonl`, `tests/test_modelos.py`, `tests/test_tools.py`.
- Modificar: `CHANGELOG.md`, `BACKLOG.md`.

## Fuera de alcance
- El verificador (002), el retrieval (003) y cualquier llamada a un LLM.
- Tiempos por ruta real (OSRM): queda detrás de la misma interfaz para más adelante (ADR-0005).
- Conversión de monedas.

## Supuestos
- **Distancia:** haversine × factor de ruta 1,3; velocidades 45 km/h en auto o traslado, 15 km/h en bici
  y 4,5 km/h a pie; minutos redondeados hacia arriba. Son estimaciones razonables para rutas rurales de
  Borgoña y se reportan como limitación.
- **Horario:** una visita está dentro del horario si empieza en o después de la apertura y termina en o
  antes del cierre. Un horario sin hora de apertura o cierre cuenta como "no se sabe".
- **Costo:** si no se elige experiencia, se toma la más barata con precio en EUR. Un precio sin moneda
  o en otra moneda no se suma: se informa en `sin_precio` (no se convierte ni se asume EUR).
- **Datos de los tests:** las bodegas de `fichas_sinteticas.jsonl` son inventadas y lo dicen en el nombre.

## Cómo se verifica
- `tests/test_modelos.py`
  - `test_hora_valida_e_invalida`: acepta "09:05", rechaza "25:00", "9:5" y "10h".
  - `test_a_minutos_y_a_hora_son_inversas`.
  - `test_bodega_desde_ficha_toma_meta`: id, zona, comuna y coordenadas salen de `_meta`; lat "" → None.
  - `test_perfil_valida_rangos`: rechaza 0 o 4 días, 0 personas, un transporte desconocido.
  - `test_cargar_corpus_saltea_lineas_invalidas`.
- `tests/test_tools.py`
  - Traslado: misma bodega → 0; caso calculado a mano en el ecuador (0,1° de longitud ≈ 11,12 km → 20, 58
    y 193 min en auto, bici y a pie); simetría; sin coordenadas → error; id inexistente → error; modo
    inválido → error.
  - Horario: 9:59 con apertura 10:00 → cerrada; 10:00 → abierta; termina justo al cierre → abierta; un
    minuto después → cerrada; día sin horario (lunes) → cerrada con motivo; bodega sin horarios → None;
    hora inválida → error en el motivo; bodega inexistente → None con error.
  - Costo: suma por personas; experiencia por nombre (sin distinguir mayúsculas); experiencia `None` → la
    más barata en EUR; sin precio, sin moneda y moneda USD → en `sin_precio`; experiencia o bodega
    inexistente → en `errores`; personas < 1 → error.
- Sensores: `make check`; `make mutation MODULO=enot/tools` con al menos 80% de mutantes muertos.
- Revisión de Flora: que los supuestos de velocidad y factor de ruta le parezcan razonables para Borgoña.
