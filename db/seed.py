"""Script de carga inicial (seeding) de AprendeGraph.

Uso:
    python -m db.seed            # crea esquema y datos (borra antes los nodos del proyecto)
    python -m db.seed --exportar # además escribe db/seed.cypher para pegarlo en la consola de Aura

Los datos son deterministas (semilla fija), así que cada carga produce el
mismo grafo y las demostraciones son reproducibles.
"""

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from app.config import ConfigError, cargar_settings
from app.database import BaseDatosNoDisponible, Neo4jClient

CARPETA = Path(__file__).parent

TEMAS = ["Python", "Bases de Datos", "Machine Learning", "Ciberseguridad",
         "Desarrollo Web", "Cloud", "Estadística", "Redes"]

INSTRUCTORES = [
    ("I01", "Mariana Ortega", "Ciencia de datos"),
    ("I02", "Javier Cauich", "Ingeniería de software"),
    ("I03", "Lucía Pech", "Seguridad informática"),
    ("I04", "Andrés Villanueva", "Infraestructura cloud"),
    ("I05", "Sofía Canul", "Bases de datos"),
    ("I06", "Diego Herrera", "Desarrollo web"),
]

# id, título, nivel, horas, temas, instructor, prerrequisitos
CURSOS = [
    ("C01", "Fundamentos de Python", "Básico", 20, ["Python"], "I02", []),
    ("C02", "Python intermedio", "Intermedio", 25, ["Python"], "I02", ["C01"]),
    ("C03", "Estadística para datos", "Básico", 18, ["Estadística"], "I01", []),
    ("C04", "Análisis de datos con Pandas", "Intermedio", 24, ["Python", "Estadística"], "I01", ["C02", "C03"]),
    ("C05", "Machine Learning I", "Intermedio", 30, ["Machine Learning", "Python"], "I01", ["C04"]),
    ("C06", "Deep Learning", "Avanzado", 36, ["Machine Learning"], "I01", ["C05"]),
    ("C07", "SQL desde cero", "Básico", 16, ["Bases de Datos"], "I05", []),
    ("C08", "Modelado relacional avanzado", "Intermedio", 22, ["Bases de Datos"], "I05", ["C07"]),
    ("C09", "Bases de datos NoSQL", "Intermedio", 20, ["Bases de Datos", "Cloud"], "I05", ["C07"]),
    ("C10", "Grafos con Neo4j", "Avanzado", 18, ["Bases de Datos"], "I05", ["C09"]),
    ("C11", "Fundamentos de redes", "Básico", 20, ["Redes"], "I04", []),
    ("C12", "Seguridad en redes", "Intermedio", 24, ["Ciberseguridad", "Redes"], "I03", ["C11"]),
    ("C13", "Hacking ético", "Avanzado", 32, ["Ciberseguridad"], "I03", ["C12", "C01"]),
    ("C14", "Operaciones de seguridad (SOC)", "Avanzado", 28, ["Ciberseguridad", "Cloud"], "I03", ["C12"]),
    ("C15", "Introducción a la nube", "Básico", 15, ["Cloud"], "I04", []),
    ("C16", "Arquitectura cloud", "Intermedio", 26, ["Cloud", "Redes"], "I04", ["C15", "C11"]),
    ("C17", "HTML, CSS y JavaScript", "Básico", 22, ["Desarrollo Web"], "I06", []),
    ("C18", "APIs con FastAPI", "Intermedio", 20, ["Desarrollo Web", "Python"], "I06", ["C02", "C17"]),
    ("C19", "Despliegue de apps en la nube", "Avanzado", 18, ["Cloud", "Desarrollo Web"], "I04", ["C18", "C16"]),
    ("C20", "Machine Learning en producción", "Avanzado", 24, ["Machine Learning", "Cloud"], "I04", ["C05", "C15"]),
]

NOMBRES = ["Ana", "Luis", "Valeria", "Diego", "Camila", "Mateo", "Fernanda", "Santiago", "Regina", "Emilio",
           "Ximena", "Iker", "Renata", "Sebastián", "Daniela", "Leonardo", "Paola", "Héctor", "Andrea", "Óscar",
           "Mariana", "Tomás", "Natalia", "Gael", "Lucía", "Rodrigo", "Elena", "Adrián", "Sara", "Pablo"]
APELLIDOS = ["Pérez", "Gómez", "May", "Chan", "Canché", "López", "Ruiz", "Ek", "Torres", "Castillo",
             "Medina", "Uc", "Navarro", "Salazar", "Pool", "Rivera", "Cetina", "Aguilar", "Vega", "Puc"]
CARRERAS = ["Ingeniería en TI", "Ingeniería en Software", "Actuaría", "Ingeniería Industrial", "Negocios Digitales"]


def generar_estudiantes(rng: random.Random) -> tuple[list[dict], list[dict], list[dict]]:
    """Crea 30 estudiantes con intereses e inscripciones coherentes con los prerrequisitos.

    Un estudiante solo se inscribe a un curso si ya terminó (progreso 100) sus
    prerrequisitos; así el seed respeta la misma regla que aplica la API.
    """
    por_id = {c[0]: c for c in CURSOS}
    estudiantes, intereses, inscripciones = [], [], []
    hoy = date(2026, 11, 1)
    for n in range(30):
        eid = f"E{n + 1:03d}"
        nombre = f"{NOMBRES[n]} {rng.choice(APELLIDOS)}"
        usuario = nombre.lower().replace(" ", ".").translate(str.maketrans("áéíóúñ", "aeioun"))
        estudiantes.append({"id": eid, "nombre": nombre, "email": f"{usuario}{n + 1}@ejemplo.com",
                            "carrera": rng.choice(CARRERAS),
                            "fecha_registro": str(hoy - timedelta(days=rng.randint(60, 300)))})
        mis_temas = rng.sample(TEMAS, 2)
        intereses += [{"estudiante": eid, "tema": t} for t in mis_temas]

        terminados: set[str] = set()
        tomados: set[str] = set()
        objetivo = rng.randint(4, 8)
        for _ in range(40):
            if len(tomados) >= objetivo:
                break
            # Preferir cursos de sus temas, pero dejar espacio para explorar otros.
            candidatos = [c for c in CURSOS if c[0] not in tomados and set(c[6]) <= terminados]
            if not candidatos:
                break
            pesos = [4 if set(c[4]) & set(mis_temas) else 1 for c in candidatos]
            curso = rng.choices(candidatos, weights=pesos)[0]
            ultimo = len(tomados) + 1 >= objetivo
            progreso = rng.choice([35, 60, 80]) if ultimo and rng.random() < 0.6 else 100
            calif = rng.choices([3, 4, 5], weights=[1, 3, 4])[0] if progreso == 100 else None
            inscripciones.append({"estudiante": eid, "curso": curso[0], "progreso": progreso,
                                  "calificacion": calif,
                                  "fecha": str(hoy - timedelta(days=290 - 35 * len(tomados) - rng.randint(0, 20)))})
            tomados.add(curso[0])
            if progreso == 100:
                terminados.add(curso[0])
        assert all(set(por_id[i["curso"]][6]) <= terminados | {i["curso"]} for i in inscripciones
                   if i["estudiante"] == eid)
    return estudiantes, intereses, inscripciones


# Las consultas de carga usan UNWIND sobre listas de parámetros: una sola
# transacción por lote en lugar de cientos de viajes de red a la nube.
LIMPIAR = """
MATCH (n) WHERE n:Estudiante OR n:Curso OR n:Tema OR n:Instructor
DETACH DELETE n
"""
CARGAR_TEMAS = "UNWIND $filas AS nombre MERGE (:Tema {nombre: nombre})"
CARGAR_INSTRUCTORES = """
UNWIND $filas AS f
MERGE (i:Instructor {id: f.id}) SET i.nombre = f.nombre, i.especialidad = f.especialidad
"""
CARGAR_CURSOS = """
UNWIND $filas AS f
MERGE (c:Curso {id: f.id})
SET c.titulo = f.titulo, c.nivel = f.nivel, c.horas = f.horas, c.descripcion = f.descripcion
WITH c, f
MATCH (i:Instructor {id: f.instructor}) MERGE (i)-[:IMPARTE]->(c)
WITH c, f
UNWIND f.temas AS tema
MATCH (t:Tema {nombre: tema}) MERGE (c)-[:CUBRE_TEMA]->(t)
"""
CARGAR_PRERREQUISITOS = """
UNWIND $filas AS f
MATCH (c:Curso {id: f.curso}), (p:Curso {id: f.requiere})
MERGE (c)-[:REQUIERE]->(p)
"""
CARGAR_ESTUDIANTES = """
UNWIND $filas AS f
MERGE (e:Estudiante {id: f.id})
SET e.nombre = f.nombre, e.email = f.email, e.carrera = f.carrera, e.fecha_registro = date(f.fecha_registro)
"""
CARGAR_INTERESES = """
UNWIND $filas AS f
MATCH (e:Estudiante {id: f.estudiante}), (t:Tema {nombre: f.tema})
MERGE (e)-[:INTERESADO_EN]->(t)
"""
CARGAR_INSCRIPCIONES = """
UNWIND $filas AS f
MATCH (e:Estudiante {id: f.estudiante}), (c:Curso {id: f.curso})
MERGE (e)-[i:INSCRITO_EN]->(c)
SET i.progreso = f.progreso, i.calificacion = f.calificacion, i.fecha = date(f.fecha)
"""


def lotes() -> list[tuple[str, str, list]]:
    """Devuelve (descripción, consulta, filas) en el orden de carga."""
    est, intereses, insc = generar_estudiantes(random.Random(42))
    cursos = [{"id": c[0], "titulo": c[1], "nivel": c[2], "horas": c[3], "temas": c[4],
               "instructor": c[5], "descripcion": f"Curso de nivel {c[2].lower()} de {c[1].lower()}."}
              for c in CURSOS]
    pre = [{"curso": c[0], "requiere": p} for c in CURSOS for p in c[6]]
    instr = [{"id": i, "nombre": n, "especialidad": e} for i, n, e in INSTRUCTORES]
    return [("temas", CARGAR_TEMAS, TEMAS), ("instructores", CARGAR_INSTRUCTORES, instr),
            ("cursos", CARGAR_CURSOS, cursos), ("prerrequisitos", CARGAR_PRERREQUISITOS, pre),
            ("estudiantes", CARGAR_ESTUDIANTES, est), ("intereses", CARGAR_INTERESES, intereses),
            ("inscripciones", CARGAR_INSCRIPCIONES, insc)]


def sentencias_esquema() -> list[str]:
    texto = (CARPETA / "schema.cypher").read_text(encoding="utf-8")
    sin_comentarios = "\n".join(l for l in texto.splitlines() if not l.strip().startswith("//"))
    return [s.strip() for s in sin_comentarios.split(";") if s.strip()]


def _literal(valor) -> str:
    """Convierte un valor de Python a literal de Cypher (para exportar el seed)."""
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, list):
        return "[" + ", ".join(_literal(v) for v in valor) + "]"
    if isinstance(valor, dict):
        return "{" + ", ".join(f"{k}: {_literal(v)}" for k, v in valor.items()) + "}"
    return '"' + str(valor).replace("\\", "\\\\").replace('"', '\\"') + '"'


def exportar_cypher() -> Path:
    """Escribe db/seed.cypher con el mismo contenido, para ejecutarlo desde la consola de Aura."""
    partes = ["// AprendeGraph: datos iniciales generados por db/seed.py (no editar a mano)",
              "// Ejecutar después de db/schema.cypher.", LIMPIAR.strip() + ";"]
    for nombre, consulta, filas in lotes():
        partes.append(f"\n// {nombre} ({len(filas)})")
        partes.append(f":param filas => {_literal(filas)};")
        partes.append(consulta.strip() + ";")
    ruta = CARPETA / "seed.cypher"
    ruta.write_text("\n".join(partes) + "\n", encoding="utf-8")
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga los datos iniciales de AprendeGraph.")
    parser.add_argument("--exportar", action="store_true", help="también genera db/seed.cypher")
    args = parser.parse_args()
    if args.exportar:
        print(f"Exportado {exportar_cypher()}")
    try:
        db = Neo4jClient(cargar_settings())
        db.conectar()
    except (ConfigError, BaseDatosNoDisponible) as exc:
        print(f"[ERROR] {exc}")
        return 1
    try:
        print(f"Conectado a {db.settings.host}")
        for sentencia in sentencias_esquema():
            db.escribir(sentencia)
        print("Esquema: restricciones e índices listos")
        db.escribir(LIMPIAR)
        for nombre, consulta, filas in lotes():
            db.escribir(consulta, filas=filas)
            print(f"  {nombre:<15} {len(filas):>4}")
        total = db.leer("MATCH (n) WHERE n:Estudiante OR n:Curso OR n:Tema OR n:Instructor "
                        "RETURN count(n) AS nodos, sum(COUNT { (n)-->() }) AS relaciones")[0]
        print(f"Listo: {total['nodos']} nodos y {total['relaciones']} relaciones en el grafo.")
    finally:
        db.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
