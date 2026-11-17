"""CRUD de la relación (:Estudiante)-[:INSCRITO_EN]->(:Curso).

La inscripción es una relación con propiedades (fecha, progreso,
calificación): en SQL sería una tabla intermedia; en el grafo es la
propia arista.
"""

from app.database import Neo4jClient

# Prerrequisitos directos del curso que el estudiante no ha terminado (progreso < 100).
PRERREQUISITOS_PENDIENTES = """
MATCH (e:Estudiante {id: $estudiante}), (c:Curso {id: $curso})
MATCH (c)-[:REQUIERE]->(pre:Curso)
WHERE NOT EXISTS { (e)-[i:INSCRITO_EN]->(pre) WHERE i.progreso = 100 }
RETURN pre.id AS id, pre.titulo AS titulo
"""

CREAR = """
MATCH (e:Estudiante {id: $estudiante}), (c:Curso {id: $curso})
MERGE (e)-[i:INSCRITO_EN]->(c)
  ON CREATE SET i.fecha = date(), i.progreso = 0, i.calificacion = null, i.creada = true
  ON MATCH SET i.creada = false
WITH i, i.creada AS nueva
REMOVE i.creada
RETURN nueva
"""

ACTUALIZAR = """
MATCH (:Estudiante {id: $estudiante})-[i:INSCRITO_EN]->(:Curso {id: $curso})
SET i.progreso = $progreso, i.calificacion = $calificacion
RETURN i.progreso AS progreso, i.calificacion AS calificacion
"""

ELIMINAR = """
MATCH (:Estudiante {id: $estudiante})-[i:INSCRITO_EN]->(:Curso {id: $curso})
DELETE i
RETURN count(*) AS eliminadas
"""


def prerrequisitos_pendientes(db: Neo4jClient, estudiante: str, curso: str) -> list[dict]:
    return db.leer(PRERREQUISITOS_PENDIENTES, estudiante=estudiante, curso=curso)


def crear(db: Neo4jClient, estudiante: str, curso: str) -> bool:
    """Devuelve True si la inscripción es nueva y False si ya existía."""
    return db.escribir(CREAR, estudiante=estudiante, curso=curso)[0]["nueva"]


def actualizar(db: Neo4jClient, estudiante: str, curso: str, progreso: int,
               calificacion: int | None) -> dict | None:
    filas = db.escribir(ACTUALIZAR, estudiante=estudiante, curso=curso,
                        progreso=progreso, calificacion=calificacion)
    return filas[0] if filas else None


def eliminar(db: Neo4jClient, estudiante: str, curso: str) -> int:
    filas = db.escribir(ELIMINAR, estudiante=estudiante, curso=curso)
    return filas[0]["eliminadas"] if filas else 0
