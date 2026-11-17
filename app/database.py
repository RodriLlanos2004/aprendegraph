"""Conexión a Neo4j con el driver oficial.

Se crea un solo Driver por proceso (es thread-safe y mantiene un pool de
conexiones) y cada consulta se ejecuta en una transacción administrada
(execute_read / execute_write). Las transacciones administradas reintentan
solas ante fallos transitorios de red o de cluster, algo importante en la
nube, donde una conexión puede cortarse entre una petición y otra.
"""

import logging
from typing import Any

from neo4j import Driver, GraphDatabase, RoutingControl, TrustSystemCAs
from neo4j.exceptions import AuthError, ServiceUnavailable

from app.config import Settings

log = logging.getLogger("aprendegraph.db")


def _uri_y_cifrado(uri: str) -> tuple[str, dict[str, Any]]:
    """Separa el esquema "+s" en opciones explícitas de cifrado.

    neo4j+s:// y neo4j:// con encrypted=True y TrustSystemCAs hacen lo mismo
    (TLS con verificación del certificado y del host). La forma explícita usa
    el almacén de certificados del sistema operativo, que en algunos equipos
    Windows reconoce cadenas (como la de SSL.com que usa Aura) que el modo
    por defecto rechaza.
    """
    for seguro, plano in (("neo4j+s://", "neo4j://"), ("bolt+s://", "bolt://")):
        if uri.startswith(seguro):
            return plano + uri[len(seguro):], {"encrypted": True, "trusted_certificates": TrustSystemCAs()}
    return uri, {}


class BaseDatosNoDisponible(RuntimeError):
    """No se pudo establecer o mantener la conexión con AuraDB."""


class Neo4jClient:
    """Envoltura mínima del driver: abrir, verificar, consultar y cerrar."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._driver: Driver | None = None

    def conectar(self) -> None:
        """Crea el driver y comprueba que la instancia responda."""
        s = self.settings
        if not s.es_nube:
            log.warning("NEO4J_URI apunta a %s: la evaluación exige una instancia en la nube.", s.host)
        uri, cifrado = _uri_y_cifrado(s.uri)
        self._driver = GraphDatabase.driver(
            uri,
            auth=(s.usuario, s.password),
            **cifrado,
            max_connection_lifetime=300,   # AuraDB cierra conexiones inactivas; se renuevan antes
            connection_acquisition_timeout=30,
        )
        try:
            self._driver.verify_connectivity()
        except AuthError as exc:
            self.cerrar()
            raise BaseDatosNoDisponible("Usuario o contraseña de Neo4j incorrectos.") from exc
        except ServiceUnavailable as exc:
            self.cerrar()
            raise BaseDatosNoDisponible(
                f"No se pudo contactar a {s.host}. Revisa la URI y que la instancia de Aura esté encendida."
            ) from exc
        log.info("Conectado a Neo4j en %s (base '%s').", s.host, s.base_datos)

    def cerrar(self) -> None:
        """Libera el pool de conexiones."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            raise BaseDatosNoDisponible("El driver no está inicializado.")
        return self._driver

    def leer(self, cypher: str, **params: Any) -> list[dict]:
        """Consulta de solo lectura. Con un cluster, se enruta a una réplica de lectura."""
        return self._ejecutar(cypher, params, RoutingControl.READ)

    def escribir(self, cypher: str, **params: Any) -> list[dict]:
        """Consulta de escritura, enrutada al líder del cluster."""
        return self._ejecutar(cypher, params, RoutingControl.WRITE)

    def _ejecutar(self, cypher: str, params: dict, ruta: RoutingControl) -> list[dict]:
        try:
            # execute_query usa por dentro una transacción administrada con reintentos.
            registros, _, _ = self.driver.execute_query(
                cypher, params, database_=self.settings.base_datos, routing_=ruta
            )
        except ServiceUnavailable as exc:
            raise BaseDatosNoDisponible("Se perdió la conexión con AuraDB. Intenta de nuevo.") from exc
        return [r.data() for r in registros]

    def info_servidor(self) -> dict:
        """Versión y edición del servidor, para mostrar en la interfaz."""
        fila = self.leer(
            "CALL dbms.components() YIELD name, versions, edition "
            "RETURN name, versions[0] AS version, edition"
        )[0]
        return {"host": self.settings.host, "cifrada": self.settings.cifrada,
                "nube": self.settings.es_nube, **fila}
