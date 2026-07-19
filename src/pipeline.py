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

import json
from pathlib import Path

from src.extract.sqlserver_connector import SQLServerExtractor
from src.transform import ejecutar_transformacion

# La etapa de Load (Integrante 4) todavia no esta implementada:
# src/load/postgres_connector.py esta vacio a la fecha de este commit.
# Se importa de forma defensiva para que Extract + Transform ya puedan
# correr de punta a punta, y en cuanto exista PostgresLoader.cargar_todo
# el pipeline lo va a usar automaticamente sin tocar este archivo.
try:
    from src.load.postgres_connector import PostgresLoader  # type: ignore
except ImportError:
    PostgresLoader = None

SALIDA_DIR = Path(__file__).resolve().parent.parent / "data" / "output"


def extraer() -> dict:
    """Etapa 1: Extract. Lee los datos crudos desde SQL Server."""
    print("Extrayendo datos desde SQL Server...")
    extractor = SQLServerExtractor()
    return extractor.extraer_todo()


def transformar(datos_crudos: dict) -> dict:
    """Etapa 2: Transform. Limpia, deduplica, fusiona y valida (Integrante 3)."""
    print("Transformando datos...")
    return ejecutar_transformacion(datos_crudos)


def cargar(resultado_transformado: dict) -> None:
    """Etapa 3: Load. Escribe el resultado en PostgreSQL si el loader ya
    esta implementado; si no, deja un respaldo en JSON para no perder el
    trabajo de Extract + Transform mientras se completa esa parte."""
    if PostgresLoader is not None:
        print("Cargando datos en PostgreSQL...")
        loader = PostgresLoader()
        loader.cargar_todo(resultado_transformado)
        return

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA_DIR / "resultado_transformado.json"
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(resultado_transformado, archivo, indent=2, default=str, ensure_ascii=False)
    print(
        "Load aun no esta implementado (src/load/postgres_connector.py vacio). "
        f"Resultado transformado guardado en: {ruta}"
    )


def mostrar_resumen(resultado: dict) -> None:
    print("\nRESUMEN DE LA TRANSFORMACION")
    print(f"  Clientes finales  : {len(resultado['clientes'])}")
    print(f"  Productos finales : {len(resultado['productos'])}")
    print(f"  Facturas          : {len(resultado['facturas'])}")
    print(f"  Detalles          : {len(resultado['detalles'])}")
    print(f"  Errores detectados: {len(resultado['errores'])}")


def ejecutar_pipeline() -> dict:
    """Orquesta el pipeline completo Extract -> Transform -> Load."""
    datos_crudos = extraer()
    resultado = transformar(datos_crudos)
    mostrar_resumen(resultado)
    cargar(resultado)
    return resultado


if __name__ == "__main__":
    ejecutar_pipeline()
