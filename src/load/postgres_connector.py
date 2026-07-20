# postgres_connector.py
"""Etapa de load

Recibe el diccionario que devuelve `ejecutar_transformacion` (Integrante 3)
-> {"clientes": [...], "productos": [...], "facturas": [...],
    "detalles": [...], "errores": [...]}
y lo carga en PostgreSQL:

  1. Conexion a PostgreSQL (settings.get_postgres_config()).
  2. Insercion de registros (clientes -> productos -> facturas -> detalles,
     en ese orden, para respetar las llaves foraneas).
  3. Evita duplicados con UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
     sobre la clave de negocio de cada tabla (documento, codigo,
     numero_factura). Un duplicado no genera una fila nueva: actualiza
     la fila existente.
  4. Maneja errores de insercion fila por fila usando SAVEPOINT: si una
     fila falla (ej. viola una constraint), se revierte SOLO esa fila y
     el resto de la carga continua. Cada error queda registrado en la
     tabla etl_carga_errores.
  5. Genera estadisticas de carga (leidos / insertados / actualizados /
     con error, y duracion) y las guarda en etl_carga_auditoria.

Uso tipico (ver pipeline.py):
    from src.load.postgres_connector import PostgresLoader

    loader = PostgresLoader()
    stats = loader.cargar_todo(resultado_transformado)

------------------------------------------------------------------------
NOTA IMPORTANTE SOBRE NOMBRES DE CAMPOS
------------------------------------------------------------------------
cleansing.py, survivorship.py y fk_reassignment.py (Integrante 3) no
estaban entre los archivos compartidos, asi que los nombres de campo
que usa este archivo se infirieron de las pistas visibles en
orchestrator.py (por ejemplo "id_cliente_origen_sobreviviente", que es
el segundo argumento de construir_mapa_sobrevivientes).

Para no tener que salir a cambiar codigo por todos lados si esos
nombres no coinciden exactamente con los reales, TODO el mapeo de
campos vive en un solo lugar: la constante COLUMN_MAP, un poco mas
abajo. Si un campo real se llama distinto, se ajusta ahi (una sola
linea) y el resto del connector sigue funcionando igual.
------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

import psycopg2

from ..settings import BATCH_SIZE, PostgresConfig, get_postgres_config

logger = logging.getLogger(__name__)

QUERIES_PATH = Path(__file__).resolve().parent / "load_queries.sql"


# ------------------------------------------------------------------
# Carga y parseo de load_queries.sql
# ------------------------------------------------------------------
def _parsear_queries(path: Path) -> dict[str, str]:
    """Convierte load_queries.sql en un diccionario {nombre: sql}.

    Cada bloque de consulta empieza con un comentario "-- name: <nombre>"
    y se extiende hasta el siguiente "-- name:" (o el fin del archivo).
    """
    texto = path.read_text(encoding="utf-8")
    bloques: dict[str, str] = {}
    nombre_actual: str | None = None
    lineas_actuales: list[str] = []

    for linea in texto.splitlines():
        marcador = linea.strip()
        if marcador.startswith("-- name:"):
            if nombre_actual is not None:
                bloques[nombre_actual] = "\n".join(lineas_actuales).strip()
            nombre_actual = marcador.replace("-- name:", "").strip()
            lineas_actuales = []
        elif nombre_actual is not None:
            lineas_actuales.append(linea)

    if nombre_actual is not None:
        bloques[nombre_actual] = "\n".join(lineas_actuales).strip()

    return bloques


# ------------------------------------------------------------------
# Mapa de columnas (ver nota al inicio del archivo)
# clave = nombre de columna que usan las queries de load_queries.sql
# valor = nombre de campo que trae el dict de Transform
# ------------------------------------------------------------------
COLUMN_MAP: dict[str, dict[str, str]] = {
    "clientes": {
        "id_cliente_origen": "id_cliente_origen_sobreviviente",
        "documento": "documento",
        "nombre": "nombre",
        "email": "email",
        "telefono": "telefono",
        "direccion": "direccion",
        "ids_origen_grupo": "ids_origen_grupo",
    },
    "productos": {
        "id_producto_origen": "id_producto_origen_sobreviviente",
        "codigo": "codigo",
        "nombre": "nombre",
        "categoria": "categoria",
        "precio": "precio",
        "ids_origen_grupo": "ids_origen_grupo",
    },
    "facturas": {
        "numero_factura": "numero_factura",
        "id_cliente_origen": "id_cliente_origen",
        "fecha_factura": "fecha_factura",
        "total": "total",
    },
    "detalles": {
        "numero_factura": "numero_factura",
        "id_producto_origen": "id_producto_origen",
        "cantidad": "cantidad",
        "precio_unitario": "precio_unitario",
    },
}


def _stats_vacio(leidos: int) -> dict[str, int]:
    return {
        "leidos": leidos,
        "insertados": 0,
        "actualizados": 0,
        "con_error": 0,
    }


class PostgresLoader:
    """Carga en PostgreSQL el resultado de la etapa de Transform."""

    def __init__(self, config: PostgresConfig | None = None):
        self.config = config or get_postgres_config()
        self.queries = _parsear_queries(QUERIES_PATH)
        self.conn = None

    # ---------------------------------------------------------
    # Conexion
    # ---------------------------------------------------------
    def conectar(self):
        """Crea (o reutiliza) la conexion a PostgreSQL."""
        if self.conn is None or self.conn.closed:
            logger.info(
                "Conectando a PostgreSQL en %s:%s/%s",
                self.config.host, self.config.port, self.config.database,
            )
            self.conn = psycopg2.connect(self.config.dsn)
            self.conn.autocommit = False
        return self.conn

    def cerrar(self) -> None:
        if self.conn is not None and not self.conn.closed:
            self.conn.close()

    def __enter__(self) -> "PostgresLoader":
        self.conectar()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cerrar()

    # ---------------------------------------------------------
    # Helper: ejecutar una fila dentro de un SAVEPOINT
    # ---------------------------------------------------------
    def _ejecutar_con_savepoint(self, cur, sql: str, params: dict) -> tuple:
        """Ejecuta 'sql' dentro de un SAVEPOINT.

        Si falla, revierte SOLO esa fila (no toda la transaccion) y
        vuelve a lanzar la excepcion para que el llamador la cuente
        como error y siga con la siguiente fila.
        """
        cur.execute("SAVEPOINT sp_fila")
        try:
            cur.execute(sql, params)
            resultado = cur.fetchone()
            cur.execute("RELEASE SAVEPOINT sp_fila")
            return resultado
        except psycopg2.Error:
            cur.execute("ROLLBACK TO SAVEPOINT sp_fila")
            raise

    def _registrar_error(self, cur, tabla: str, identificador: Any, mensaje: str, registro: dict) -> None:
        """Guarda un error de insercion en etl_carga_errores y lo loguea."""
        logger.warning("Error cargando %s (clave=%s): %s", tabla, identificador, mensaje)
        try:
            cur.execute("SAVEPOINT sp_error")
            cur.execute(
                self.queries["insertar_error_carga"],
                {
                    "tabla": tabla,
                    "identificador_registro": str(identificador),
                    "mensaje_error": mensaje,
                    "registro_json": json.dumps(registro, default=str, ensure_ascii=False),
                },
            )
            cur.execute("RELEASE SAVEPOINT sp_error")
        except psycopg2.Error as exc:
            # Si ni siquiera se pudo registrar el error (ej. la BD se cayo),
            # no queremos que esto tumbe toda la carga: solo lo logueamos.
            cur.execute("ROLLBACK TO SAVEPOINT sp_error")
            logger.error("No se pudo registrar el error de carga en la BD: %s", exc)

    # ---------------------------------------------------------
    # Carga por tabla
    # ---------------------------------------------------------
    def _cargar_clientes(self, clientes: list[dict]) -> tuple[dict, dict]:
        """Inserta/actualiza clientes. Devuelve (stats, mapa_ids) donde
        mapa_ids traduce id_cliente_origen -> id_cliente (serial de Postgres),
        necesario despues para resolver la FK de facturas."""
        mapa_campos = COLUMN_MAP["clientes"]
        query = self.queries["upsert_cliente"]
        stats = _stats_vacio(len(clientes))
        mapa_ids: dict[Any, int] = {}

        cur = self.conn.cursor()
        for i, c in enumerate(clientes, start=1):
            id_origen = c.get(mapa_campos["id_cliente_origen"])
            params = {destino: c.get(origen) for destino, origen in mapa_campos.items()}
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                mapa_ids[id_origen] = nuevo_id
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "clientes", params.get("documento", id_origen), str(exc), c)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats, mapa_ids

    def _cargar_productos(self, productos: list[dict]) -> tuple[dict, dict]:
        mapa_campos = COLUMN_MAP["productos"]
        query = self.queries["upsert_producto"]
        stats = _stats_vacio(len(productos))
        mapa_ids: dict[Any, int] = {}

        cur = self.conn.cursor()
        for i, p in enumerate(productos, start=1):
            id_origen = p.get(mapa_campos["id_producto_origen"])
            params = {destino: p.get(origen) for destino, origen in mapa_campos.items()}
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                mapa_ids[id_origen] = nuevo_id
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "productos", params.get("codigo", id_origen), str(exc), p)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats, mapa_ids

    def _cargar_facturas(self, facturas: list[dict], mapa_ids_clientes: dict) -> tuple[dict, dict]:
        """Inserta/actualiza facturas, resolviendo id_cliente_origen ->
        id_cliente (Postgres) con el mapa que devolvio _cargar_clientes."""
        mapa_campos = COLUMN_MAP["facturas"]
        query = self.queries["upsert_factura"]
        stats = _stats_vacio(len(facturas))
        mapa_ids: dict[str, int] = {}

        cur = self.conn.cursor()
        for i, f in enumerate(facturas, start=1):
            numero_factura = f.get(mapa_campos["numero_factura"])
            id_cliente_origen = f.get(mapa_campos["id_cliente_origen"])
            id_cliente_pg = mapa_ids_clientes.get(id_cliente_origen)

            if id_cliente_pg is None:
                stats["con_error"] += 1
                self._registrar_error(
                    cur, "facturas", numero_factura,
                    f"Cliente origen {id_cliente_origen!r} no fue cargado previamente "
                    "(revisar deduplicacion/reasignacion de FKs en Transform)",
                    f,
                )
                continue

            params = {
                "numero_factura": numero_factura,
                "id_cliente_origen": id_cliente_origen,
                "id_cliente": id_cliente_pg,
                "fecha_factura": f.get(mapa_campos["fecha_factura"]),
                "total": f.get(mapa_campos["total"]),
            }
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                mapa_ids[numero_factura] = nuevo_id
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "facturas", numero_factura, str(exc), f)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats, mapa_ids

    def _cargar_detalles(self, detalles: list[dict], mapa_ids_productos: dict, mapa_ids_facturas: dict) -> dict:
        """Inserta/actualiza detalles, resolviendo id_producto_origen ->
        id_producto y numero_factura -> id_factura."""
        mapa_campos = COLUMN_MAP["detalles"]
        query = self.queries["upsert_detalle"]
        stats = _stats_vacio(len(detalles))

        cur = self.conn.cursor()
        for i, d in enumerate(detalles, start=1):
            numero_factura = d.get(mapa_campos["numero_factura"])
            id_producto_origen = d.get(mapa_campos["id_producto_origen"])
            id_factura_pg = mapa_ids_facturas.get(numero_factura)
            id_producto_pg = mapa_ids_productos.get(id_producto_origen)

            if id_factura_pg is None or id_producto_pg is None:
                stats["con_error"] += 1
                self._registrar_error(
                    cur, "detalles", f"{numero_factura}/{id_producto_origen}",
                    f"No se pudo resolver factura (encontrada={id_factura_pg is not None}) "
                    f"o producto (encontrado={id_producto_pg is not None}) para este detalle",
                    d,
                )
                continue

            params = {
                "numero_factura": numero_factura,
                "id_factura": id_factura_pg,
                "id_producto_origen": id_producto_origen,
                "id_producto": id_producto_pg,
                "cantidad": d.get(mapa_campos["cantidad"]),
                "precio_unitario": d.get(mapa_campos["precio_unitario"]),
            }
            try:
                _id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "detalles", f"{numero_factura}/{id_producto_origen}", str(exc), d)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats

    # ---------------------------------------------------------
    # Estadisticas de carga
    # ---------------------------------------------------------
    def _guardar_auditoria(self, stats_por_tabla: dict[str, tuple[dict, float]]) -> None:
        """Escribe una fila por tabla en etl_carga_auditoria."""
        cur = self.conn.cursor()
        for tabla, (stats, duracion) in stats_por_tabla.items():
            cur.execute(
                self.queries["insertar_auditoria_carga"],
                {
                    "tabla": tabla,
                    "registros_leidos": stats["leidos"],
                    "registros_insertados": stats["insertados"],
                    "registros_actualizados": stats["actualizados"],
                    "registros_con_error": stats["con_error"],
                    "duracion_segundos": round(duracion, 3),
                },
            )
        self.conn.commit()
        cur.close()

    def _mostrar_resumen(self, stats_por_tabla: dict[str, tuple[dict, float]]) -> None:
        print("\nRESUMEN DE LA CARGA A POSTGRESQL")
        for tabla, (stats, duracion) in stats_por_tabla.items():
            print(
                f"  {tabla:<10} | leidos={stats['leidos']:<5} "
                f"insertados={stats['insertados']:<5} "
                f"actualizados={stats['actualizados']:<5} "
                f"con_error={stats['con_error']:<5} "
                f"({duracion:.2f}s)"
            )

    # ---------------------------------------------------------
    # Punto de entrada principal
    # ---------------------------------------------------------
    def cargar_todo(self, resultado_transformado: dict) -> dict:
        """Carga clientes, productos, facturas y detalles, en ese orden
        (respetando las FKs), y devuelve un resumen de estadisticas.

        Parametros
        ----------
        resultado_transformado: dict devuelto por
            transform.orchestrator.ejecutar_transformacion(...)

        Retorna
        -------
        dict {"clientes": stats, "productos": stats, "facturas": stats,
              "detalles": stats} donde cada stats es
              {"leidos", "insertados", "actualizados", "con_error"}.
        """
        self.conectar()
        stats_por_tabla: dict[str, tuple[dict, float]] = {}

        t0 = time.time()
        stats_clientes, mapa_ids_clientes = self._cargar_clientes(
            resultado_transformado.get("clientes", [])
        )
        stats_por_tabla["clientes"] = (stats_clientes, time.time() - t0)

        t0 = time.time()
        stats_productos, mapa_ids_productos = self._cargar_productos(
            resultado_transformado.get("productos", [])
        )
        stats_por_tabla["productos"] = (stats_productos, time.time() - t0)

        t0 = time.time()
        stats_facturas, mapa_ids_facturas = self._cargar_facturas(
            resultado_transformado.get("facturas", []), mapa_ids_clientes
        )
        stats_por_tabla["facturas"] = (stats_facturas, time.time() - t0)

        t0 = time.time()
        stats_detalles = self._cargar_detalles(
            resultado_transformado.get("detalles", []), mapa_ids_productos, mapa_ids_facturas
        )
        stats_por_tabla["detalles"] = (stats_detalles, time.time() - t0)

        self._guardar_auditoria(stats_por_tabla)
        self._mostrar_resumen(stats_por_tabla)

        return {tabla: stats for tabla, (stats, _duracion) in stats_por_tabla.items()}


# ----------------------------------------------------------------
# Ejecucion standalone: util para probar solo la etapa de Load,
# reutilizando el respaldo JSON que pipeline.py genera cuando esta
# etapa todavia no existia (data/output/resultado_transformado.json).
# ----------------------------------------------------------------
def _cargar_desde_json_de_respaldo() -> dict:
    ruta = Path(__file__).resolve().parents[2] / "data" / "output" / "resultado_transformado.json"
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    datos = _cargar_desde_json_de_respaldo()
    with PostgresLoader() as loader:
        loader.cargar_todo(datos)
