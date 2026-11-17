"""Modelos de entrada (validación con Pydantic) de la API."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Nivel = Literal["Básico", "Intermedio", "Avanzado"]


class _Limpio(BaseModel):
    """Quita espacios sobrantes en todos los textos."""

    model_config = {"str_strip_whitespace": True}


class EstudianteIn(_Limpio):
    nombre: str = Field(min_length=3, max_length=80)
    email: EmailStr
    carrera: str = Field(min_length=2, max_length=80)
    intereses: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("email")
    @classmethod
    def email_minusculas(cls, v: str) -> str:
        return v.lower()


class CursoIn(_Limpio):
    titulo: str = Field(min_length=3, max_length=100)
    nivel: Nivel
    horas: int = Field(ge=1, le=300)
    descripcion: str = Field(default="", max_length=400)
    temas: list[str] = Field(min_length=1, max_length=6)
    instructor_id: str | None = None
    requiere: list[str] = Field(default_factory=list, max_length=6)


class InscripcionIn(_Limpio):
    estudiante: str
    curso: str


class AvanceIn(BaseModel):
    progreso: int = Field(ge=0, le=100)
    calificacion: int | None = Field(default=None, ge=1, le=5)
