"""CRUD del nodo :Estudiante y sus intereses (:INTERESADO_EN -> :Tema)."""

from app.database import Neo4jClient

LISTAR = """
MATCH (e:Estudiante)
OPTIONAL MATCH (e)-[:INSCRITO_EN]->(c:Curso)
RETURN e.id AS id, e.nombre AS nombre, e.email AS email, e.carrera AS carrera,
       count(c) AS cursos
ORDER BY e.nombre
"""

OBTENER = """
MATCH (e:Estudiante {id: $id})
OPTIONAL MATCH (e)-[:INTERESADO_EN]->(t:Tema)
WITH e, collect(t.nombre) AS intereses
OPTIONAL MATCH (e)-[i:INSCRITO_EN]->(c:Curso)
WITH e, intereses, i, c ORDER BY i.fecha
RETURN e {.id, .nombre, .email, .carrera, fecha_registro: toString(e.fecha_registro)} AS estudiante,
       intereses,
       [x IN collect({id: c.id, titulo: c.titulo, progreso: i.progreso,
                      calificacion: i.calificacion, fecha: toString(i.fecha)}) WHERE x.id IS NOT NULL] AS inscripciones
"""

CREAR = """
CREATE (e:Estudiante {id: $id, nombre: $nombre, email: $email, carrera: $carrera,
                      fecha_registro: date()})
WITH e
UNWIND $intereses AS tema
MATCH (t:Tema {nombre: tema})
MERGE (e)-[:INTERESADO_EN]->(t)
RETURN count(*) AS intereses
"""

ACTUALIZAR = """
MATCH (e:Estudiante {id: $id})
SET e.nombre = $nombre, e.email = $email, e.carrera = $carrera
WITH e
OPTIONAL MATCH (e)-[old:INTERESADO_EN]->(:Tema)
DELETE old
WITH DISTINCT e
UNWIND $intereses AS tema
MATCH (t:Tema {nombre: tema})
MERGE (e)-[:INTERESADO_EN]->(t)
RETURN count(*) AS intereses
"""

EXISTE = "MATCH (e:Estudiante {id: $id}) RETURN e.id AS id"

ELIMINAR = """
MATCH (e:Estudiante {id: $id})
WITH e, e.nombre AS nombre
DETACH DELETE e
RETURN nombre
"""


def listar(db: Neo4jClient) -> list[dict]:
    return db.leer(LISTAR)


def obtener(db: Neo4jClient, id_: str) -> dict | None:
    filas = db.leer(OBTENER, id=id_)
    return filas[0] if filas else None


def existe(db: Neo4jClient, id_: str) -> bool:
    return bool(db.leer(EXISTE, id=id_))


def crear(db: Neo4jClient, datos: dict) -> None:
    db.escribir(CREAR, **datos)


def actualizar(db: Neo4jClient, datos: dict) -> None:
    db.escribir(ACTUALIZAR, **datos)


def eliminar(db: Neo4jClient, id_: str) -> str | None:
    filas = db.escribir(ELIMINAR, id=id_)
    return filas[0]["nombre"] if filas else None
