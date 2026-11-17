"""Inyección de dependencias: entrega a cada endpoint el cliente de Neo4j compartido."""

from fastapi import Request

from app.database import Neo4jClient


def get_db(request: Request) -> Neo4jClient:
    return request.app.state.db
