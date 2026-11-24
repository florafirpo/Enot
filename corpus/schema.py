"""Esquema de la ficha de bodega (PRD, sección 5). Independiente de la región.

Es lo que el LLM tiene que devolver. Regla de oro: si un dato no está en el
texto, va null. Cada dato importante tiene que venir con su evidencia (cita
textual + URL), así después podemos medir alucinaciones sin trabajo manual.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Dia = Literal["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


class Horario(BaseModel):
    dias: list[Dia] = Field(description="Días a los que aplica este horario")
    apertura: Optional[str] = Field(None, description="HH:MM, 24 h")
    cierre: Optional[str] = Field(None, description="HH:MM, 24 h")


class Experiencia(BaseModel):
    nombre: str = Field(description="Nombre tal como lo publica la bodega")
    tipo: Literal["visita_guiada", "degustacion", "maridaje", "almuerzo", "cena", "picnic",
                  "cabalgata", "bicicleta", "clase_o_taller", "otro"]
    duracion_min: Optional[int] = Field(None, description="Duración en minutos, si figura")
    precio_por_persona: Optional[float] = Field(
        None, description="Número tal como figura, sin convertir moneda. null si dice 'consultar'")
    moneda: Optional[Literal["EUR", "USD", "ARS", "otra"]] = None
    precio_texto: Optional[str] = Field(None, description="El precio como está escrito, ej. '15 € par personne'")
    idiomas: list[str] = Field(default_factory=list)
    horarios_salida: list[str] = Field(default_factory=list, description="Turnos, ej. ['10:00', '12:30']")
    incluye: Optional[str] = Field(None, description="Qué vinos/platos incluye, resumido")
    requiere_reserva: Optional[bool] = None


class Evidencia(BaseModel):
    campo: str = Field(description="Nombre del campo que respalda, ej. 'experiencias[0].precio_por_persona'")
    cita: str = Field(description="Fragmento textual copiado EXACTO del texto fuente (máx. ~200 caracteres)")
    url: str = Field(description="URL de la sección 'Fuente:' de donde sale la cita")


class FichaBodega(BaseModel):
    nombre: str
    descripcion_breve: Optional[str] = Field(None, description="1 o 2 oraciones, con palabras propias")
    perfil: Literal["boutique", "familiar", "mediana", "grande", "no_informado"] = "no_informado"
    abre_al_turismo: Optional[bool] = Field(None, description="True si el texto ofrece visitas o experiencias al público")
    horarios: list[Horario] = Field(default_factory=list)
    horario_texto: Optional[str] = Field(None, description="Horario tal como está escrito")
    requiere_reserva: Optional[bool] = None
    experiencias: list[Experiencia] = Field(default_factory=list)
    tiene_restaurante: Optional[bool] = None
    opciones_sin_tacc: Optional[bool] = None
    opciones_vegetarianas: Optional[bool] = None
    opciones_veganas: Optional[bool] = None
    notas_gastronomia: Optional[str] = None
    accesible_movilidad_reducida: Optional[bool] = None
    acepta_grupos: Optional[bool] = None
    capacidad_max_grupo: Optional[int] = None
    acepta_menores: Optional[bool] = None
    idiomas: list[str] = Field(default_factory=list)
    vinos_o_varietales_destacados: list[str] = Field(default_factory=list)
    email: Optional[str] = None
    telefono: Optional[str] = None
    url_reservas: Optional[str] = None
    evidencias: list[Evidencia] = Field(default_factory=list)


# Campos que miramos en el EDA de completitud (PRD, sección 5)
CAMPOS_COMPLETITUD = [
    "descripcion_breve", "perfil", "abre_al_turismo", "horarios|horario_texto", "requiere_reserva",
    "experiencias", "precio (alguna experiencia)", "tiene_restaurante", "opciones_sin_tacc",
    "opciones_vegetarianas", "accesible_movilidad_reducida", "acepta_grupos", "capacidad_max_grupo",
    "idiomas", "vinos_o_varietales_destacados", "email|telefono", "url_reservas",
]
