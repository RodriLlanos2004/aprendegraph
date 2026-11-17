"""Endpoints de recomendaciones, caminos y vecindades."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencias import get_db
from app.repositories import cursos, estudiantes
from app.repositories import recomendaciones as repo

router = APIRouter(prefix="/api", tags=["Grafo"])


def _estudiante(db, id_: str) -> None:
    if not estudiantes.existe(db, id_):
        raise HTTPException(404, f"No existe el estudiante {id_}.")


@router.get("/recomendaciones/{id_}")
def recomendaciones(id_: str, limite: int = Query(5, ge=1, le=20), db=Depends(get_db)):
    _estudiante(db, id_)
    return {
        "colaborativo": repo.colaborativo(db, id_, limite),
        "contenido": repo.contenido(db, id_, limite),
        "afines": repo.afines(db, id_, limite),
    }


@router.get("/ruta/{estudiante}/{curso}")
def ruta(estudiante: str, curso: str, db=Depends(get_db)):
    _estudiante(db, estudiante)
    if not cursos.existe(db, curso):
        raise HTTPException(404, f"No existe el curso {curso}.")
    return repo.ruta(db, estudiante, curso)


@router.get("/conexion/{origen}/{destino}")
def conexion(origen: str, destino: str, db=Depends(get_db)):
    _estudiante(db, origen)
    _estudiante(db, destino)
    if origen == destino:
        raise HTTPException(422, "Elige dos estudiantes distintos.")
    fila = repo.conexion(db, origen, destino)
    if fila is None:
        raise HTTPException(404, "No hay ningún camino entre esos estudiantes.")
    return fila


@router.get("/subgrafo/{id_}")
def subgrafo(id_: str, db=Depends(get_db)):
    _estudiante(db, id_)
    return repo.subgrafo(db, id_)
