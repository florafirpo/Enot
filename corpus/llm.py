"""Cliente mínimo de LLM con salida estructurada, sin frameworks.

Soporta:
- openai             : API de OpenAI (structured outputs con json_schema)
- openai_compatible  : cualquier endpoint compatible (Ollama, OpenRouter, Groq, vLLM...).
                       Se configura con OPENAI_BASE_URL. Si el endpoint no acepta
                       json_schema, cae a json_object con el esquema en el prompt.
- anthropic          : API de Anthropic, forzando una tool cuyo input es el esquema.

Devuelve el objeto validado con Pydantic + uso de tokens + latencia, para el
registro de costos que pide la consigna.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


@dataclass
class Resultado:
    objeto: BaseModel
    tokens_in: int
    tokens_out: int
    latencia_s: float
    intentos: int


class ErrorSalidaInvalida(RuntimeError):
    """El modelo no devolvió una salida válida en `intentos` llamadas. Trae los tokens que se gastaron en esas
    llamadas (exactos), para que el reporte de costos no los cuente como 0 (spec 008)."""

    def __init__(self, mensaje: str, tokens_in: int, tokens_out: int, intentos: int):
        super().__init__(mensaje)
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.intentos = intentos


def esquema_sin_refs(modelo: Type[BaseModel]) -> dict:
    """Pydantic genera $defs/$ref; algunos proveedores los manejan mal. Los inlineamos."""
    esquema = modelo.model_json_schema()
    defs = esquema.pop("$defs", {})

    def resolver(nodo):
        if isinstance(nodo, dict):
            if "$ref" in nodo:
                nombre = nodo["$ref"].split("/")[-1]
                return resolver(dict(defs[nombre]))
            return {k: resolver(v) for k, v in nodo.items()}
        if isinstance(nodo, list):
            return [resolver(x) for x in nodo]
        return nodo

    return resolver(esquema)


class ClienteLLM:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or config.LLM_PROVIDER
        self.model = model or config.LLM_MODEL
        if self.provider == "anthropic":
            import anthropic
            self.cli = anthropic.Anthropic()
        elif self.provider in {"openai", "openai_compatible"}:
            from openai import OpenAI
            kwargs = {}
            if config.OPENAI_BASE_URL:
                kwargs["base_url"] = config.OPENAI_BASE_URL
            if self.provider == "openai_compatible":
                import os
                kwargs.setdefault("api_key", os.getenv("OPENAI_API_KEY", "no-hace-falta"))
            self.cli = OpenAI(**kwargs)
            self._json_schema_ok = True
        else:
            raise ValueError(f"LLM_PROVIDER desconocido: {self.provider}")

    # ------------------------------------------------------------------
    def estructurado(self, sistema: str, usuario: str, modelo: Type[T],
                     max_intentos: int = 2) -> Resultado:
        """Pide una salida que valide contra `modelo`. Si no valida, reintenta
        devolviéndole el error al LLM (un loop de verificación chiquito)."""
        esquema = esquema_sin_refs(modelo)
        mensajes_extra: list[tuple[str, str]] = []
        tin = tout = 0
        t0 = time.perf_counter()
        ultimo_error = None
        for intento in range(1, max_intentos + 1):
            crudo, i_in, i_out = self._llamar(sistema, usuario, esquema, modelo.__name__, mensajes_extra)
            tin, tout = tin + i_in, tout + i_out
            try:
                datos = crudo if isinstance(crudo, dict) else json.loads(crudo)
                obj = modelo.model_validate(datos)
                return Resultado(obj, tin, tout, time.perf_counter() - t0, intento)
            except (json.JSONDecodeError, ValidationError) as e:
                ultimo_error = e
                mensajes_extra = [
                    ("assistant", crudo if isinstance(crudo, str) else json.dumps(crudo, ensure_ascii=False)),
                    ("user", f"La salida no valida contra el esquema. Error:\n{str(e)[:2000]}\n"
                             "Devolvé el JSON corregido completo."),
                ]
        raise ErrorSalidaInvalida(f"No se obtuvo una salida válida tras {max_intentos} intentos: {ultimo_error}",
                                  tin, tout, max_intentos)

    # ------------------------------------------------------------------
    def _llamar(self, sistema, usuario, esquema, nombre, extra):
        if self.provider == "anthropic":
            return self._anthropic(sistema, usuario, esquema, nombre, extra)
        return self._openai(sistema, usuario, esquema, nombre, extra)

    def _openai(self, sistema, usuario, esquema, nombre, extra):
        msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]
        msgs += [{"role": r, "content": c} for r, c in extra]
        kwargs = dict(model=self.model, messages=msgs, **self._params_muestreo())
        if self._json_schema_ok:
            try:
                r = self._crear(**kwargs, response_format={
                    "type": "json_schema",
                    "json_schema": {"name": nombre, "schema": esquema, "strict": False}})
            except Exception as e:  # noqa: BLE001 — endpoints compatibles sin json_schema
                if "response_format" not in str(e) and "json_schema" not in str(e):
                    raise
                self._json_schema_ok = False
                return self._openai(sistema, usuario, esquema, nombre, extra)
        else:
            msgs[0]["content"] = (sistema + "\n\nRespondé SOLO con un JSON que valide contra este "
                                  "JSON Schema:\n" + json.dumps(esquema, ensure_ascii=False))
            r = self._crear(**kwargs, response_format={"type": "json_object"})
        u = r.usage
        return (r.choices[0].message.content or "",
                getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0)

    # Los modelos de razonamiento de OpenAI rechazan temperature y piden
    # max_completion_tokens; los endpoints compatibles suelen querer max_tokens.
    # Arrancamos con lo clásico y nos adaptamos al primer error.
    _sin_temperature = False
    _usar_max_completion = False

    def _params_muestreo(self) -> dict:
        p = {}
        if not self._sin_temperature:
            p["temperature"] = 0
        p["max_completion_tokens" if self._usar_max_completion else "max_tokens"] = config.MAX_TOKENS_SALIDA
        return p

    def _crear(self, **kwargs):
        for _ in range(3):
            try:
                return self.cli.chat.completions.create(**kwargs)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "temperature" in msg and "temperature" in kwargs:
                    self._sin_temperature = True
                    kwargs.pop("temperature")
                elif "max_tokens" in msg and "max_tokens" in kwargs:
                    self._usar_max_completion = True
                    kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
                else:
                    raise
        return self.cli.chat.completions.create(**kwargs)

    def _anthropic(self, sistema, usuario, esquema, nombre, extra):
        msgs = [{"role": "user", "content": usuario}]
        msgs += [{"role": r, "content": c} for r, c in extra]
        r = self.cli.messages.create(
            model=self.model, max_tokens=config.MAX_TOKENS_SALIDA, temperature=0, system=sistema,
            messages=msgs,
            tools=[{"name": f"guardar_{nombre.lower()}",
                    "description": "Guarda la ficha estructurada extraída del texto.",
                    "input_schema": esquema}],
            tool_choice={"type": "tool", "name": f"guardar_{nombre.lower()}"},
        )
        bloque = next((b for b in r.content if b.type == "tool_use"), None)
        datos = bloque.input if bloque else ""
        return datos, r.usage.input_tokens, r.usage.output_tokens
