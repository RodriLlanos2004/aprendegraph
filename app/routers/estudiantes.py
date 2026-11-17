"""Endpoints CRUD de estudiantes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j.exceptions import ConstraintError

from app.dependencias import get_db
from app.repositories import estudiantes as repo
from app.schemas import EstudianteIn

router = APIRouter(prefix="/api/estudiantes", tags=["Estudiantes"])


@router.get("")
def listar(db=Depends(get_db)):
    return repo.listar(db)


@router.get("/{id_}")
def obtener(id_: str, db=Depends(get_db)):
    fila = repo.obtener(db, id_)
    if fila is None:
        raise HTTPException(404, f"No existe el estudiante {id_}.")
    return fila


@router.post("", status_code=status.HTTP_201_CREATED)
def crear(datos: EstudianteIn, db=Depends(get_db)):
    nuevo_id = "E-" + uuid.uuid4().hex[:6].upper()
    try:
        repo.crear(db, {"id": nuevo_id, **datos.model_dump()})
    except ConstraintError:
        # La restricción UNIQUE de Neo4j sobre Estudiante.email detiene el duplicado.
        raise HTTPException(409, f"Ya existe un estudiante con el email {datos.email}.")
    return {"id": nuevo_id}


@router.put("/{id_}")
def actualizar(id_: str, datos: EstudianteIn, db=Depends(get_db)):
    if not repo.existe(db, id_):
        raise HTTPException(404, f"No existe el estudiante {id_}.")
    try:
        repo.actualizar(db, {"id": id_, **datos.model_dump()})
    except ConstraintError:
        raise HTTPException(409, f"El email {datos.email} ya pertenece a otro estudiante.")
    return {"id": id_}


@router.delete("/{id_}")
def eliminar(id_: str, db=Depends(get_db)):
    nombre = repo.eliminar(db, id_)
    if nombre is None:
        raise HTTPException(404, f"No existe el estudiante {id_}.")
    return {"eliminado": nombre}
