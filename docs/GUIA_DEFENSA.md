# Guía para la demostración y la defensa

Este archivo es para preparar la exposición; no forma parte de la entrega al profesor.

## Antes de entrar al examen

1. La víspera, entra a https://console.neo4j.io y confirma que la instancia está en Running. Si está pausada, reanúdala (tarda un par de minutos).
2. Ejecuta `python -m db.seed` para dejar los datos limpios.
3. Arranca `uvicorn app.main:app` y abre http://localhost:8000 antes de que te toque.
4. Ten abierta también la consola de Aura en la pestaña Query, por si piden ver los datos directo en la base.

## Guion de la demostración (4 minutos)

1. **Conexión (20 s).** Señala el encabezado: versión de Neo4j, host `*.databases.neo4j.io` y conteo de nodos. "La base está en AuraDB, no en mi máquina."
2. **CRUD (1 min).** En Estudiantes crea uno con dos intereses, edítalo y ábrelo con Ver. En Cursos edita un curso y enseña que cambian sus temas.
3. **Regla de negocio (40 s).** En Recomendaciones intenta inscribir al estudiante nuevo en "Python intermedio": la app lo rechaza porque falta "Fundamentos de Python". Inscríbelo en Fundamentos, marca 100 % de avance y luego sí deja inscribirlo.
4. **Recomendaciones (1 min).** Elige a un estudiante con varios cursos (E028). Explica las tres columnas y el grafo de vecindad.
5. **Ruta y conexión (40 s).** Ruta de E001 hacia "Despliegue de apps en la nube"; conexión entre dos estudiantes.
6. **Persistencia (20 s).** Recarga la página o vuelve a la consola de Aura y ejecuta `MATCH (e:Estudiante) RETURN count(e)` para mostrar que el estudiante creado sigue ahí. Al final elimínalo.

## Preguntas probables y cómo responderlas

**¿Por qué grafo y no SQL?**
Porque las preguntas son recorridos: recomendar es ir de un estudiante a sus cursos, a otros estudiantes y a sus cursos (3 saltos), y la ruta de prerrequisitos tiene profundidad variable. En SQL serían tres JOIN de la misma tabla o un WITH RECURSIVE. En Neo4j cada nodo apunta directo a sus relaciones (adyacencia sin índice), así que el costo depende de la vecindad recorrida, no del tamaño total de las tablas.

**¿Por qué no clave-valor?**
Redis es excelente para buscar por clave exacta o para datos con expiración, pero no recorre relaciones. Cada salto obligaría a la app a pedir claves y unirlas en memoria.

**¿Cómo se conecta la app con la nube?**
Con el driver oficial `neo4j` de Python, por el protocolo Bolt sobre TLS (`neo4j+s://`). Se crea un único driver al arrancar (tiene un pool de conexiones) y se cierra al apagar el servidor.

**¿La conexión va cifrada? ¿Por qué `TrustSystemCAs`?**
Sí. Bolt viaja sobre TLS y el driver verifica el certificado del servidor y el nombre del host. En mi equipo el modo por defecto de `neo4j+s://` rechazaba la cadena del certificado de Aura (emitido por SSL.com), así que lo configuré explícito: `encrypted=True` con `TrustSystemCAs()`, que valida contra los certificados de confianza del sistema operativo. No se desactivó ninguna verificación.

**¿Dónde están las credenciales?**
En variables de entorno cargadas desde `.env`, que está en `.gitignore`. El repositorio solo trae `.env.example`.

**¿Qué pasa si se cae la conexión?**
`execute_query` usa transacciones administradas que reintentan solas ante fallos transitorios. Si Aura no responde, la API devuelve 503 con un mensaje claro y la app no se rompe.

**¿Cómo evitas inyección de Cypher?**
Todas las consultas usan parámetros (`$id`, `$nombre`); nunca se concatena texto del usuario en la consulta.

**¿Qué consistencia ofrece Neo4j?**
Es ACID: una operación se guarda completa o no se guarda. En cluster, las escrituras se confirman por consenso (Raft), así que ante una partición de red prioriza la consistencia (CP en el teorema CAP). Aura Free es una sola instancia.

**¿Cómo garantizas que no se repitan datos?**
Restricciones de unicidad en `Estudiante.id`, `Estudiante.email`, `Curso.id`, `Tema.nombre` e `Instructor.id`. Si se intenta un email repetido, Neo4j lanza `ConstraintError` y la API responde 409. Cada restricción crea también un índice.

**¿Por qué la inscripción es una relación y no un nodo?**
Porque sus datos (fecha, progreso, calificación) describen el vínculo entre estudiante y curso. Sería nodo si tuviera relaciones propias, por ejemplo pagos o constancias.

**¿Qué diferencia hay entre CREATE y MERGE?**
CREATE siempre crea; MERGE busca el patrón y solo lo crea si no existe. Por eso la inscripción usa MERGE: inscribir dos veces no duplica la relación.

**¿Y DELETE frente a DETACH DELETE?**
DELETE falla si el nodo tiene relaciones; DETACH DELETE borra primero sus relaciones. Para eliminar un estudiante se usa DETACH DELETE.

**¿Cómo funciona la recomendación colaborativa?**
Desde el estudiante se va a sus cursos, de ahí a los otros inscritos y luego a los cursos de ellos que él no tomó. Se cuentan cuántos estudiantes afines llevaron cada curso y se ordena por ese número y por la calificación promedio.

**¿Qué es la similitud de Jaccard?**
Cursos en común entre los cursos distintos de los dos estudiantes. Va de 0 (nada en común) a 1 (los mismos cursos).

**¿Qué hace `[:REQUIERE*1..]`?**
Es un patrón de longitud variable: sigue la relación REQUIERE uno o más saltos, sin saber de antemano la profundidad. Así se obtienen los prerrequisitos de los prerrequisitos.

**¿Cómo evitas ciclos de prerrequisitos?**
Antes de guardar, una consulta revisa si el nuevo prerrequisito ya depende del curso que se edita. Si es así, la API responde 409.

**¿Qué pasa con el rendimiento si crecen los datos?**
Las búsquedas por id usan los índices de las restricciones; los recorridos dependen de la vecindad. La carga inicial va por lotes con UNWIND (una transacción por lote) para no hacer cientos de viajes de red a la nube.

**¿Cuáles son los límites de Aura Free?**
Una base de datos, 200 mil nodos y 400 mil relaciones, sin respaldos, y se pausa tras 72 horas sin uso.
