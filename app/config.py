"""Configuración leída desde variables de entorno (archivo .env).

Las credenciales nunca se escriben en el código: se cargan del entorno
para que el repositorio pueda ser público sin exponer la base de datos.
"""

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

_HOSTS_LOCALES = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


class ConfigError(RuntimeError):
    """Falta una variable de entorno obligatoria o tiene un valor inválido."""


@dataclass(frozen=True)
class Settings:
    """Parámetros de conexión a Neo4j AuraDB."""

    uri: str
    usuario: str
    password: str
    base_datos: str

    @property
    def host(self) -> str:
        """Host de la instancia, sin credenciales (para mostrarlo en la interfaz)."""
        return urlparse(self.uri).hostname or ""

    @property
    def es_nube(self) -> bool:
        """True si la URI apunta a un servicio remoto y no a la máquina local."""
        return self.host not in _HOSTS_LOCALES

    @property
    def cifrada(self) -> bool:
        """True si el esquema exige TLS (neo4j+s o bolt+s), como pide AuraDB."""
        return urlparse(self.uri).scheme.endswith("+s")


def _obligatoria(nombre: str) -> str:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        raise ConfigError(
            f"Falta la variable de entorno {nombre}. Copia .env.example a .env y completa tus datos de AuraDB."
        )
    return valor


def cargar_settings() -> Settings:
    """Lee y valida la configuración. Lanza ConfigError con un mensaje claro si algo falta."""
    return Settings(
        uri=_obligatoria("NEO4J_URI"),
        usuario=_obligatoria("NEO4J_USERNAME"),
        password=_obligatoria("NEO4J_PASSWORD"),
        base_datos=os.getenv("NEO4J_DATABASE", "neo4j").strip() or "neo4j",
    )
