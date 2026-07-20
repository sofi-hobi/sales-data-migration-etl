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




def validar_transformacion(datos_crudos: dict, resultado: dict) -> None:
    """Detiene la carga ante pérdidas críticas de registros o FKs.

    Los errores de calidad (correo/fecha/teléfono) son esperados y se auditan,
    pero no se permite perder facturas, detalles ni total monetario.
    """
    cantidad_clientes_origen = len(datos_crudos.get("clientes", []))
    if cantidad_clientes_origen < 1000:
        raise RuntimeError(
            f"La base origen debe tener al menos 1000 clientes; se extrajeron {cantidad_clientes_origen}."
        )

    if len(resultado.get("facturas", [])) != len(datos_crudos.get("facturas", [])):
        raise RuntimeError("La transformación perdió facturas.")
    if len(resultado.get("detalles", [])) != len(datos_crudos.get("detalles", [])):
        raise RuntimeError("La transformación perdió detalles de factura.")

    total_origen = round(sum(float(f.get("Total") or 0) for f in datos_crudos.get("facturas", [])), 2)
    total_transformado = round(sum(float(f.get("total") or 0) for f in resultado.get("facturas", [])), 2)
    if abs(total_origen - total_transformado) > 0.01:
        raise RuntimeError(
            f"El total monetario cambió durante Transform: origen={total_origen}, transformado={total_transformado}."
        )

    clientes_validos = {c["id_cliente_origen_sobreviviente"] for c in resultado.get("clientes", [])}
    productos_validos = {p["id_producto_origen_sobreviviente"] for p in resultado.get("productos", [])}
    facturas_validas = {f["id_factura_origen"] for f in resultado.get("facturas", [])}
    if any(f["id_cliente_origen"] not in clientes_validos for f in resultado.get("facturas", [])):
        raise RuntimeError("Existen facturas sin cliente maestro después de la reasignación.")
    if any(d["id_factura_origen"] not in facturas_validas for d in resultado.get("detalles", [])):
        raise RuntimeError("Existen detalles sin factura después de la transformación.")
    if any(d["id_producto_origen"] not in productos_validos for d in resultado.get("detalles", [])):
        raise RuntimeError("Existen detalles sin producto maestro después de la reasignación.")


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
    validar_transformacion(datos_crudos, resultado)
    mostrar_resumen(resultado)
    stats_carga = cargar(resultado)

    errores_carga = sum(
        stats.get("con_error", 0)
        for nombre, stats in stats_carga.items()
        if isinstance(stats, dict) and nombre in {"clientes", "productos", "facturas", "detalles", "mapeos_clientes"}
    )
    if errores_carga:
        raise RuntimeError(f"El Load terminó con {errores_carga} errores técnicos.")

    print("\n✅ Pipeline ETL completado exitosamente y validado.")
    return resultado


if __name__ == "__main__":
    ejecutar_pipeline()
