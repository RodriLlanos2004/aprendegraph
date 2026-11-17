"""CRUD del nodo :Curso con sus temas, instructor y prerrequisitos."""

from app.database import Neo4jClient

LISTAR = """
MATCH (c:Curso)
OPTIONAL MATCH (c)-[:CUBRE_TEMA]->(t:Tema)
WITH c, collect(t.nombre) AS temas
OPTIONAL MATCH (i:Instructor)-[:IMPARTE]->(c)
OPTIONAL MATCH (c)-[:REQUIERE]->(p:Curso)
WITH c, temas, i, collect(p.id) AS requiere
OPTIONAL MATCH (:Estudiante)-[r:INSCRITO_EN]->(c)
RETURN c.id AS id, c.titulo AS titulo, c.nivel AS nivel, c.horas AS horas,
       temas, i.nombre AS instructor, requiere,
       count(r) AS inscritos, round(avg(r.calificacion), 2) AS calificacion
ORDER BY c.id
"""

OBTENER = """
MATCH (c:Curso {id: $id})
OPTIONAL MATCH (c)-[:CUBRE_TEMA]->(t:Tema)
WITH c, collect(t.nombre) AS temas
OPTIONAL MATCH (i:Instructor)-[:IMPARTE]->(c)
OPTIONAL MATCH (c)-[:REQUIERE]->(p:Curso)
RETURN c {.id, .titulo, .nivel, .horas, .descripcion} AS curso, temas,
       i.id AS instructor_id, i.nombre AS instructor,
       collect(p {.id, .titulo}) AS requiere
"""

CREAR = """
CREATE (c:Curso {id: $id, titulo: $titulo, nivel: $nivel, horas: $horas, descripcion: $descripcion})
WITH c
CALL (c) {
  UNWIND $temas AS tema
  MATCH (t:Tema {nombre: tema})
  MERGE (c)-[:CUBRE_TEMA]->(t)
}
CALL (c) {
  OPTIONAL MATCH (i:Instructor {id: $instructor_id})
  FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END | MERGE (i)-[:IMPARTE]->(c))
}
CALL (c) {
  UNWIND $requiere AS pre_id
  MATCH (p:Curso {id: pre_id})
  MERGE (c)-[:REQUIERE]->(p)
}
RETURN c.id AS id
"""

# Reemplaza propiedades y vuelve a tender las relaciones salientes del curso.
ACTUALIZAR = """
MATCH (c:Curso {id: $id})
SET c.titulo = $titulo, c.nivel = $nivel, c.horas = $horas, c.descripcion = $descripcion
WITH c
CALL (c) {
  MATCH (c)-[r:CUBRE_TEMA|REQUIERE]->() DELETE r
}
CALL (c) {
  MATCH (:Instructor)-[r:IMPARTE]->(c) DELETE r
}
CALL (c) {
  UNWIND $temas AS tema
  MATCH (t:Tema {nombre: tema})
  MERGE (c)-[:CUBRE_TEMA]->(t)
}
CALL (c) {
  OPTIONAL MATCH (i:Instructor {id: $instructor_id})
  FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END | MERGE (i)-[:IMPARTE]->(c))
}
CALL (c) {
  UNWIND $requiere AS pre_id
  MATCH (p:Curso {id: pre_id}) WHERE p <> c
  MERGE (c)-[:REQUIERE]->(p)
}
RETURN c.id AS id
"""

# Evita ciclos de prerrequisitos: si el nuevo prerrequisito ya depende de este curso,
# agregarlo cerraría un ciclo y la ruta de aprendizaje sería infinita.
CICLO = """
MATCH (c:Curso {id: $id}), (p:Curso) WHERE p.id IN $requiere
MATCH ruta = (p)-[:REQUIERE*1..]->(c)
RETURN p.titulo AS curso LIMIT 1
"""

EXISTE = "MATCH (c:Curso {id: $id}) RETURN c.id AS id"

ELIMINAR = """
MATCH (c:Curso {id: $id})
OPTIONAL MATCH (dep:Curso)-[:REQUIERE]->(c)
WITH c, c.titulo AS titulo, collect(dep.titulo) AS dependientes
DETACH DELETE c
RETURN titulo, dependientes
"""

TEMAS = "MATCH (t:Tema) RETURN t.nombre AS nombre ORDER BY nombre"
FALTANTES = """
RETURN [t IN $temas WHERE NOT EXISTS { MATCH (:Tema {nombre: t}) }] AS temas,
       [p IN $requiere WHERE NOT EXISTS { MATCH (:Curso {id: p}) }] AS cursos
"""
INSTRUCTORES = "MATCH (i:Instructor) RETURN i.id AS id, i.nombre AS nombre ORDER BY nombre"


def listar(db: Neo4jClient) -> list[dict]:
    return db.leer(LISTAR)


def obtener(db: Neo4jClient, id_: str) -> dict | None:
    filas = db.leer(OBTENER, id=id_)
    return filas[0] if filas else None


def existe(db: Neo4jClient, id_: str) -> bool:
    return bool(db.leer(EXISTE, id=id_))


def crea_ciclo(db: Neo4jClient, id_: str, requiere: list[str]) -> str | None:
    filas = db.leer(CICLO, id=id_, requiere=requiere)
    return filas[0]["curso"] if filas else None


def crear(db: Neo4jClient, datos: dict) -> None:
    db.escribir(CREAR, **datos)


def actualizar(db: Neo4jClient, datos: dict) -> None:
    db.escribir(ACTUALIZAR, **datos)


def eliminar(db: Neo4jClient, id_: str) -> dict | None:
    filas = db.escribir(ELIMINAR, id=id_)
    return filas[0] if filas else None


def referencias_faltantes(db: Neo4jClient, temas_: list[str], requiere: list[str]) -> tuple[list, list]:
    """Temas y prerrequisitos que no existen en el grafo (para rechazar la petición)."""
    fila = db.leer(FALTANTES, temas=temas_, requiere=requiere)[0]
    return fila["temas"], fila["cursos"]


def temas(db: Neo4jClient) -> list[str]:
    return [f["nombre"] for f in db.leer(TEMAS)]


def instructores(db: Neo4jClient) -> list[dict]:
    return db.leer(INSTRUCTORES)
