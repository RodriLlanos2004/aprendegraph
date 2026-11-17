"""Consultas propias del paradigma de grafos: traversals, caminos y vecindades.

Estas son las consultas que justifican haber elegido Neo4j: cada una recorre
varias relaciones a partir de un nodo, algo que en SQL requeriría varios JOIN
o consultas recursivas (WITH RECURSIVE) cuyo costo crece con el tamaño de las
tablas y no con el tamaño de la vecindad recorrida.
"""

from app.database import Neo4jClient

# Filtrado colaborativo: "estudiantes que tomaron tus cursos también tomaron...".
# Recorrido de 3 saltos: yo -> curso <- otro -> recomendado.
COLABORATIVO = """
MATCH (yo:Estudiante {id: $id})-[:INSCRITO_EN]->(:Curso)<-[:INSCRITO_EN]-(otro:Estudiante)
WITH DISTINCT yo, otro
MATCH (otro)-[r:INSCRITO_EN]->(rec:Curso)
WHERE NOT EXISTS { (yo)-[:INSCRITO_EN]->(rec) }
WITH yo, rec, count(otro) AS afines, avg(r.calificacion) AS calificacion
OPTIONAL MATCH (rec)-[:REQUIERE]->(pre:Curso)
WHERE NOT EXISTS { (yo)-[i:INSCRITO_EN]->(pre) WHERE i.progreso = 100 }
RETURN rec.id AS id, rec.titulo AS titulo, rec.nivel AS nivel, afines,
       round(calificacion, 2) AS calificacion,
       collect(pre.titulo) AS prerrequisitos_pendientes
ORDER BY afines DESC, calificacion DESC
LIMIT $limite
"""

# Basado en contenido: cursos que cubren los temas que le interesan al estudiante
# o los temas de los cursos que ya tomó.
CONTENIDO = """
MATCH (yo:Estudiante {id: $id})
OPTIONAL MATCH (yo)-[:INTERESADO_EN]->(t1:Tema)
OPTIONAL MATCH (yo)-[:INSCRITO_EN]->(:Curso)-[:CUBRE_TEMA]->(t2:Tema)
WITH yo, collect(DISTINCT t1) + collect(DISTINCT t2) AS temas
UNWIND temas AS t
WITH yo, collect(DISTINCT t) AS temas
MATCH (rec:Curso)-[:CUBRE_TEMA]->(t:Tema)
WHERE t IN temas AND NOT EXISTS { (yo)-[:INSCRITO_EN]->(rec) }
WITH yo, rec, collect(t.nombre) AS coincidencias
OPTIONAL MATCH (rec)-[:REQUIERE]->(pre:Curso)
WHERE NOT EXISTS { (yo)-[i:INSCRITO_EN]->(pre) WHERE i.progreso = 100 }
RETURN rec.id AS id, rec.titulo AS titulo, rec.nivel AS nivel, coincidencias,
       collect(pre.titulo) AS prerrequisitos_pendientes
ORDER BY size(coincidencias) DESC, size(prerrequisitos_pendientes), rec.titulo
LIMIT $limite
"""

# Vecindad: compañeros con cursos en común, ordenados por similitud de Jaccard
# (cursos en común / cursos distintos entre los dos).
AFINES = """
MATCH (yo:Estudiante {id: $id})-[:INSCRITO_EN]->(c:Curso)<-[:INSCRITO_EN]-(otro:Estudiante)
WITH yo, otro, collect(c.titulo) AS comunes
WITH yo, otro, comunes, COUNT { (yo)-[:INSCRITO_EN]->() } AS mios,
     COUNT { (otro)-[:INSCRITO_EN]->() } AS suyos
RETURN otro.id AS id, otro.nombre AS nombre, comunes,
       round(toFloat(size(comunes)) / (mios + suyos - size(comunes)), 3) AS jaccard
ORDER BY jaccard DESC, size(comunes) DESC
LIMIT $limite
"""

# Ruta de aprendizaje: todos los prerrequisitos (directos e indirectos) del curso meta,
# con recorrido de longitud variable. La profundidad máxima ordena los pasos.
RUTA = """
MATCH (meta:Curso {id: $curso})
OPTIONAL MATCH camino = (meta)-[:REQUIERE*1..]->(pre:Curso)
WITH meta, pre, max(length(camino)) AS profundidad
OPTIONAL MATCH (:Estudiante {id: $estudiante})-[i:INSCRITO_EN]->(pre)
WITH meta, pre, profundidad, coalesce(i.progreso, -1) AS progreso
ORDER BY profundidad DESC, pre.titulo
RETURN meta.titulo AS meta,
       [x IN collect({id: pre.id, titulo: pre.titulo, nivel: pre.nivel,
                      profundidad: profundidad, progreso: progreso}) WHERE x.id IS NOT NULL] AS pasos
"""

# Camino más corto entre dos estudiantes a través de cursos compartidos
# ("grados de separación"). Se ignora la dirección de las relaciones.
CONEXION = """
MATCH (a:Estudiante {id: $origen}), (b:Estudiante {id: $destino})
MATCH camino = shortestPath((a)-[:INSCRITO_EN*..8]-(b))
RETURN [n IN nodes(camino) | {id: n.id, nombre: coalesce(n.nombre, n.titulo),
                               tipo: labels(n)[0]}] AS nodos,
       length(camino) AS saltos
"""

# Vecindad a 2 saltos para dibujar el subgrafo del estudiante.
SUBGRAFO = """
MATCH (yo:Estudiante {id: $id})
CALL (yo) {
  MATCH (yo)-[r:INSCRITO_EN|INTERESADO_EN]->(n)
  RETURN r, n AS a, n AS b
  UNION
  MATCH (yo)-[:INSCRITO_EN]->(c:Curso)-[r:CUBRE_TEMA|REQUIERE]->(n)
  RETURN r, c AS a, n AS b
  UNION
  MATCH (yo)-[:INSCRITO_EN]->(c:Curso)<-[r:IMPARTE]-(n:Instructor)
  RETURN r, n AS a, c AS b
}
WITH yo, collect(DISTINCT r) AS rels
UNWIND rels AS r
WITH yo, r, startNode(r) AS s, endNode(r) AS t
RETURN collect(DISTINCT {id: elementId(r), desde: elementId(s), hacia: elementId(t), tipo: type(r)}) AS aristas,
       [n IN collect(DISTINCT s) + collect(DISTINCT t) |
          {id: elementId(n), tipo: labels(n)[0], nombre: coalesce(n.nombre, n.titulo)}] AS nodos
"""


def colaborativo(db: Neo4jClient, id_: str, limite: int = 5) -> list[dict]:
    return db.leer(COLABORATIVO, id=id_, limite=limite)


def contenido(db: Neo4jClient, id_: str, limite: int = 5) -> list[dict]:
    return db.leer(CONTENIDO, id=id_, limite=limite)


def afines(db: Neo4jClient, id_: str, limite: int = 5) -> list[dict]:
    return db.leer(AFINES, id=id_, limite=limite)


def ruta(db: Neo4jClient, estudiante: str, curso: str) -> dict | None:
    filas = db.leer(RUTA, estudiante=estudiante, curso=curso)
    return filas[0] if filas else None


def conexion(db: Neo4jClient, origen: str, destino: str) -> dict | None:
    filas = db.leer(CONEXION, origen=origen, destino=destino)
    return filas[0] if filas else None


def subgrafo(db: Neo4jClient, id_: str) -> dict:
    filas = db.leer(SUBGRAFO, id=id_)
    if not filas:
        return {"nodos": [], "aristas": []}
    nodos = {n["id"]: n for n in filas[0]["nodos"]}  # quita duplicados
    return {"nodos": list(nodos.values()), "aristas": filas[0]["aristas"]}
