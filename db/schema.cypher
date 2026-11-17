// =====================================================================
// AprendeGraph: esquema del grafo (restricciones e índices)
// Neo4j es "schema-optional": no exige esquema, pero estas reglas
// garantizan identificadores únicos y aceleran las búsquedas por id.
// Cada restricción UNIQUE crea también un índice sobre la propiedad.
// =====================================================================

CREATE CONSTRAINT estudiante_id IF NOT EXISTS
FOR (e:Estudiante) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT estudiante_email IF NOT EXISTS
FOR (e:Estudiante) REQUIRE e.email IS UNIQUE;

CREATE CONSTRAINT curso_id IF NOT EXISTS
FOR (c:Curso) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT tema_nombre IF NOT EXISTS
FOR (t:Tema) REQUIRE t.nombre IS UNIQUE;

CREATE CONSTRAINT instructor_id IF NOT EXISTS
FOR (i:Instructor) REQUIRE i.id IS UNIQUE;

// Índice de apoyo para filtrar el catálogo por nivel.
CREATE INDEX curso_nivel IF NOT EXISTS
FOR (c:Curso) ON (c.nivel);
