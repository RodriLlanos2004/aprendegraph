# AprendeGraph

Recomendador de cursos en línea construido sobre una base de datos de grafos en la nube (Neo4j AuraDB). Backend en Python con FastAPI y el driver oficial de Neo4j; interfaz web incluida.

Funciones principales:

- CRUD de estudiantes, cursos e inscripciones (la inscripción es una relación con propiedades).
- Recomendación colaborativa: "quienes tomaron tus cursos también tomaron".
- Recomendación por temas compartidos.
- Compañeros afines por similitud de Jaccard (vecindad del estudiante).
- Ruta de aprendizaje: prerrequisitos directos e indirectos de un curso meta.
- Camino más corto entre dos estudiantes con `shortestPath`.

La documentación de diseño y justificación está en `docs/AprendeGraph_Documentacion.pdf`.

## Requisitos

- Python 3.10 o superior.
- Una instancia de Neo4j AuraDB (la capa Free basta: hasta 200 mil nodos y 400 mil relaciones).
- Conexión a internet (la base de datos está en la nube).

## 1. Crear la base de datos en Neo4j AuraDB

1. Entra a https://console.neo4j.io y crea una cuenta (no pide tarjeta).
2. Pulsa **Create instance** y elige **AuraDB Free**.
3. Al crearse, la consola muestra la contraseña y ofrece **descargar un archivo .txt con las credenciales**. Descárgalo: la contraseña no se vuelve a mostrar.
4. Espera a que la instancia aparezca como **Running** (uno o dos minutos).

Importante: una instancia Free se **pausa sola tras 72 horas sin uso**. Antes de una demostración, entra a la consola y reanúdala con el botón de play. Si pasa 30 días pausada, Aura la elimina.

## 2. Instalar

```bash
git clone https://github.com/RodriLlanos2004/aprendegraph.git
cd aprendegraph
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configurar credenciales

Copia `.env.example` como `.env` y llena los valores del archivo que descargaste de Aura:

```
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=la-contraseña-de-aura
NEO4J_DATABASE=neo4j
```

El archivo `.env` está en `.gitignore`: las credenciales nunca se suben al repositorio.

## 4. Cargar el esquema y los datos iniciales

```bash
python -m db.seed
```

Crea las restricciones e índices de `db/schema.cypher` y carga 8 temas, 6 instructores, 20 cursos, 30 estudiantes y 178 inscripciones (64 nodos y 307 relaciones). Los datos son deterministas: se puede ejecutar las veces que haga falta y siempre deja el mismo grafo. Solo borra nodos de este proyecto.

Alternativa sin Python: pega `db/schema.cypher` y luego `db/seed.cypher` en la pestaña Query de la consola de Aura. `seed.cypher` se regenera con `python -m db.seed --exportar`.

## 5. Ejecutar

```bash
uvicorn app.main:app --reload
```

- Aplicación: http://localhost:8000
- Documentación interactiva de la API (Swagger): http://localhost:8000/docs

El encabezado de la aplicación muestra la versión de Neo4j, el host de Aura y el conteo de nodos y relaciones, lo que confirma la conexión con la nube.

## Estructura

```
app/
  config.py           variables de entorno y validación
  database.py         driver de Neo4j (pool, transacciones administradas)
  dependencias.py     inyección del cliente en los endpoints
  schemas.py          validación de entrada con Pydantic
  main.py             aplicación FastAPI
  repositories/       una función por consulta Cypher
  routers/            endpoints REST
  static/             interfaz web (HTML, CSS, JS)
db/
  schema.cypher       restricciones de unicidad e índices
  seed.py             carga inicial por lotes con UNWIND
  seed.cypher         la misma carga en Cypher puro
docs/                 documentación PDF
```

## Endpoints

- `GET|POST /api/estudiantes`, `GET|PUT|DELETE /api/estudiantes/{id}`
- `GET|POST /api/cursos`, `GET|PUT|DELETE /api/cursos/{id}`
- `POST /api/inscripciones`, `PUT|DELETE /api/inscripciones/{estudiante}/{curso}`
- `GET /api/recomendaciones/{id}`
- `GET /api/ruta/{estudiante}/{curso}`
- `GET /api/conexion/{origen}/{destino}`
- `GET /api/subgrafo/{id}`
- `GET /api/estado`

## Solución de problemas

- **"No se pudo contactar a ..."**: la instancia está pausada o la URI está mal. Reanúdala en la consola de Aura.
- **"Usuario o contraseña de Neo4j incorrectos"**: revisa el `.env`; la contraseña es la del archivo descargado de Aura.
- **`CERTIFICATE_VERIFY_FAILED` al conectar**: el modo por defecto de `neo4j+s://` no reconoce la cadena del certificado de Aura en ese equipo. `app/database.py` ya lo resuelve: conecta con `encrypted=True` y `TrustSystemCAs()`, que valida el certificado con las autoridades del sistema operativo (sigue cifrado y verificado).
- **Aviso "NEO4J_URI apunta a localhost"**: estás usando una base local; para la evaluación debe ser la URI `neo4j+s://` de Aura.
