"""Endpoints de inscripciones (CRUD de la relación INSCRITO_EN)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencias import get_db
from app.repositories import cursos, estudiantes
from app.repositories import inscripciones as repo
from app.schemas import AvanceIn, InscripcionIn

router = APIRouter(prefix="/api/inscripciones", tags=["Inscripciones"])


@router.post("", status_code=status.HTTP_201_CREATED)
def inscribir(datos: InscripcionIn, db=Depends(get_db)):
    if not estudiantes.existe(db, datos.estudiante):
        raise HTTPException(404, f"No existe el estudiante {datos.estudiante}.")
    if not cursos.existe(db, datos.curso):
        raise HTTPException(404, f"No existe el curso {datos.curso}.")
    # Regla de negocio resuelta con el grafo: hay que terminar los prerrequisitos antes.
    pendientes = repo.prerrequisitos_pendientes(db, datos.estudiante, datos.curso)
    if pendientes:
        titulos = ", ".join(p["titulo"] for p in pendientes)
        raise HTTPException(409, f"Primero debe terminar: {titulos}.")
    if not repo.crear(db, datos.estudiante, datos.curso):
        raise HTTPException(409, "El estudiante ya estaba inscrito en ese curso.")
    return {"inscrito": True}


@router.put("/{estudiante}/{curso}")
def actualizar(estudiante: str, curso: str, avance: AvanceIn, db=Depends(get_db)):
    fila = repo.actualizar(db, estudiante, curso, avance.progreso, avance.calificacion)
    if fila is None:
        raise HTTPException(404, "No existe esa inscripción.")
    return fila


@router.delete("/{estudiante}/{curso}")
def eliminar(estudiante: str, curso: str, db=Depends(get_db)):
    if repo.eliminar(db, estudiante, curso) == 0:
        raise HTTPException(404, "No existe esa inscripción.")
    return {"eliminada": True}
