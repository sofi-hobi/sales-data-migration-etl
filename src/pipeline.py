# pipeline.py
"""Punto de entrada del pipeline ETL completo: Extract -> Transform -> Load.

Conecta las tres etapas construidas por el equipo:
  1. Extract   (Integrante 2): src/extract/sqlserver_connector.py
  2. Transform (Integrante 3): src/transform/orchestrator.py
  3. Load      (Integrante 4): src/load/postgres_connector.py

Uso:
    python -m src.pipeline
"""
from __future__ import annotations

from src.config.logging_config import configure_logging
from src.extract.sqlserver_connector import SQLServerExtractor
from src.transform import ejecutar_transformacion
from src.load.postgres_connector import PostgresLoader


def extraer() -> dict:
    """Etapa 1: Extract. Lee los datos crudos desde SQL Server."""
    print("🚀 Extrayendo datos desde SQL Server...")
    extractor = SQLServerExtractor()
    return extractor.extraer_todo()


def transformar(datos_crudos: dict) -> dict:
    """Etapa 2: Transform. Limpia, deduplica, fusiona y valida."""
    print("🔄 Transformando datos...")
    return ejecutar_transformacion(datos_crudos)


def cargar(resultado_transformado: dict) -> dict:
    """Etapa 3: Load. Escribe el resultado en PostgreSQL."""
    print("📥 Cargando datos en PostgreSQL...")
    with PostgresLoader() as loader:
        return loader.cargar_todo(resultado_transformado)


def mostrar_resumen(resultado: dict) -> None:
    print("\n📊 RESUMEN DE LA TRANSFORMACIÓN")
    print(f"  Clientes finales  : {len(resultado['clientes'])}")
    print(f"  Productos finales : {len(resultado['productos'])}")
    print(f"  Facturas          : {len(resultado['facturas'])}")
    print(f"  Detalles          : {len(resultado['detalles'])}")
    print(f"  Errores detectados: {len(resultado['errores'])}")


def ejecutar_pipeline() -> dict:
    """Orquesta el pipeline completo Extract -> Transform -> Load."""
    configure_logging()

    datos_crudos = extraer()
    resultado = transformar(datos_crudos)
    mostrar_resumen(resultado)
    stats_carga = cargar(resultado)

    print("\n✅ Pipeline ETL completado exitosamente.")
    return resultado


if __name__ == "__main__":
    ejecutar_pipeline()
