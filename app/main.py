"""Punto de entrada de AprendeGraph.

Ejecutar con:  uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import cargar_settings
from app.database import BaseDatosNoDisponible, Neo4jClient
from app.routers import cursos, estudiantes, inscripciones, recomendaciones

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre la conexión al iniciar el servidor y la cierra al apagarlo."""
    db = Neo4jClient(cargar_settings())
    db.conectar()
    app.state.db = db
    yield
    db.cerrar()


app = FastAPI(title="AprendeGraph", version="1.0",
              description="Recomendador de cursos en línea sobre Neo4j AuraDB", lifespan=lifespan)

for r in (estudiantes.router, cursos.router, inscripciones.router, recomendaciones.router):
    app.include_router(r)


@app.exception_handler(BaseDatosNoDisponible)
async def sin_base(_: Request, exc: BaseDatosNoDisponible):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/api/estado", tags=["Sistema"])
def estado(request: Request):
    """Datos de la instancia conectada y conteo de nodos y relaciones."""
    db: Neo4jClient = request.app.state.db
    conteo = db.leer(
        "CALL () { MATCH (n) RETURN count(n) AS nodos } "
        "CALL () { MATCH ()-[r]->() RETURN count(r) AS relaciones } "
        "RETURN nodos, relaciones"
    )[0]
    return {**db.info_servidor(), **conteo}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(STATIC / "index.html")
