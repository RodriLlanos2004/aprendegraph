"""Endpoints CRUD de cursos y catálogos auxiliares (temas, instructores)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencias import get_db
from app.repositories import cursos as repo
from app.schemas import CursoIn

router = APIRouter(prefix="/api", tags=["Cursos"])


@router.get("/cursos")
def listar(db=Depends(get_db)):
    return repo.listar(db)


@router.get("/cursos/{id_}")
def obtener(id_: str, db=Depends(get_db)):
    fila = repo.obtener(db, id_)
    if fila is None:
        raise HTTPException(404, f"No existe el curso {id_}.")
    return fila


def _validar_referencias(db, datos: CursoIn) -> None:
    temas, cursos = repo.referencias_faltantes(db, datos.temas, datos.requiere)
    if temas:
        raise HTTPException(422, f"Temas inexistentes: {', '.join(temas)}.")
    if cursos:
        raise HTTPException(422, f"Prerrequisitos inexistentes: {', '.join(cursos)}.")


@router.post("/cursos", status_code=status.HTTP_201_CREATED)
def crear(datos: CursoIn, db=Depends(get_db)):
    _validar_referencias(db, datos)
    nuevo_id = "C-" + uuid.uuid4().hex[:6].upper()
    repo.crear(db, {"id": nuevo_id, **datos.model_dump()})
    return {"id": nuevo_id}


@router.put("/cursos/{id_}")
def actualizar(id_: str, datos: CursoIn, db=Depends(get_db)):
    if not repo.existe(db, id_):
        raise HTTPException(404, f"No existe el curso {id_}.")
    if id_ in datos.requiere:
        raise HTTPException(422, "Un curso no puede ser prerrequisito de sí mismo.")
    _validar_referencias(db, datos)
    ciclo = repo.crea_ciclo(db, id_, datos.requiere)
    if ciclo:
        raise HTTPException(409, f"'{ciclo}' ya depende de este curso: se formaría un ciclo de prerrequisitos.")
    repo.actualizar(db, {"id": id_, **datos.model_dump()})
    return {"id": id_}


@router.delete("/cursos/{id_}")
def eliminar(id_: str, db=Depends(get_db)):
    fila = repo.eliminar(db, id_)
    if fila is None:
        raise HTTPException(404, f"No existe el curso {id_}.")
    return {"eliminado": fila["titulo"], "dejaron_de_requerirlo": fila["dependientes"]}


@router.get("/temas")
def temas(db=Depends(get_db)):
    return repo.temas(db)


@router.get("/instructores")
def instructores(db=Depends(get_db)):
    return repo.instructores(db)
