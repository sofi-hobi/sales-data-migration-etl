"""Configuracion centralizada del pipeline ETL, leida desde variables de entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SqlServerConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    driver: str = "{ODBC Driver 18 for SQL Server}"

    @property
    def odbc_connection_string(self) -> str:
        return (
            f"DRIVER={self.driver};"
            f"SERVER={self.host},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.user};PWD={self.password};"
            "TrustServerCertificate=yes;"
        )


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Falta la variable de entorno requerida: {name}")
    return value


def get_sqlserver_config() -> SqlServerConfig:
    """Por defecto apunta al contenedor 'sqlserver' expuesto en docker-compose.yml."""
    return SqlServerConfig(
        host=_env("SQLSERVER_HOST", "localhost"),
        port=int(_env("SQLSERVER_PORT", "1435")),
        database=_env("SQLSERVER_DATABASE", "SmartCleanOrigen"),
        user=_env("SQLSERVER_USER", "sa"),
        password=_env("SQLSERVER_PASSWORD", "Grupo1@BDD!"),
    )


def get_postgres_config() -> PostgresConfig:
    """Por defecto apunta al contenedor 'postgres' expuesto en docker-compose.yml."""
    return PostgresConfig(
        host=_env("POSTGRES_HOST", "localhost"),
        port=int(_env("POSTGRES_PORT", "5432")),
        database=_env("POSTGRES_DB", "etl_destino"),
        user=_env("POSTGRES_USER", "etl_user"),
        password=_env("POSTGRES_PASSWORD", "Grupo1_PG!"),
    )


# Tamano de lote sugerido para futuras optimizaciones de carga masiva.
BATCH_SIZE = int(os.getenv("ETL_BATCH_SIZE", "500"))
