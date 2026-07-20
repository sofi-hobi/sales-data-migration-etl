# postgres_connector.py
"""Etapa de Load del pipeline ETL: SQL Server → PostgreSQL.

Recibe el diccionario que devuelve `ejecutar_transformacion` (Integrante 3)
-> {"clientes": [...], "productos": [...], "facturas": [...],
    "detalles": [...], "errores": [...]}
y lo carga en PostgreSQL:

  1. Conexión a PostgreSQL (settings.get_postgres_config()).
  2. Inserción de registros (clientes -> productos -> facturas -> detalles,
     en ese orden, para respetar las llaves foráneas).
  3. Evita duplicados con UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
     sobre la clave de negocio de cada tabla (documento, codigo_producto,
     numero_factura). Un duplicado no genera una fila nueva: actualiza
     la fila existente.
  4. Maneja errores de inserción fila por fila usando SAVEPOINT: si una
     fila falla (ej. viola una constraint), se revierte SOLO esa fila y
     el resto de la carga continúa. Cada error queda registrado en la
     tabla etl_carga_errores.
  5. Genera estadísticas de carga (leídos / insertados / actualizados /
     con error, y duración) y las guarda en etl_carga_auditoria.

Uso típico (ver pipeline.py):
    from src.load.postgres_connector import PostgresLoader

    loader = PostgresLoader()
    stats = loader.cargar_todo(resultado_transformado)

------------------------------------------------------------------------
MAPEO DE CAMPOS
------------------------------------------------------------------------
Todo el mapeo entre los nombres que usa Transform (snake_case) y los
nombres de las columnas de PostgreSQL vive en la constante COLUMN_MAP.
Si Transform cambia un nombre de campo, se ajusta ahí y el resto del
connector sigue funcionando igual.
------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import psycopg2

from ..config.settings import BATCH_SIZE, PostgresConfig, get_postgres_config

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
# Mapa de columnas
# clave = nombre de parámetro en la query de load_queries.sql
# valor = nombre de campo en el dict que devuelve Transform
# ------------------------------------------------------------------
COLUMN_MAP: dict[str, dict[str, str]] = {
    "clientes": {
        "id_cliente_origen": "id_cliente_origen_sobreviviente",
        "documento": "documento",
        "nombre": "nombre",
        "apellido": "apellido",
        "correo": "correo",
        "telefono": "telefono",
        "direccion": "direccion",
        "ciudad": "ciudad",
        "fecha_nacimiento": "fecha_nacimiento",
        "fecha_registro": "fecha_registro",
        "estado": "estado",
        "ids_origen_grupo": "ids_origen_grupo",
    },
    "productos": {
        "id_producto_origen": "id_producto_origen_sobreviviente",
        "codigo_producto": "codigo_producto",
        "nombre_producto": "nombre_producto",
        "categoria": "categoria",
        "precio": "precio",
        "estado": "estado",
        "ids_origen_grupo": "ids_origen_grupo",
    },
    "facturas": {
        "id_factura_origen": "id_factura_origen",
        "numero_factura": "numero_factura",
        "id_cliente_origen": "id_cliente_origen",
        "fecha_emision": "fecha_emision",
        "estado": "estado",
        "subtotal": "subtotal",
        "iva": "iva",
        "total": "total",
    },
    "detalles": {
        "id_detalle_origen": "id_detalle_origen",
        "id_factura_origen": "id_factura_origen",
        "id_producto_origen": "id_producto_origen",
        "cantidad": "cantidad",
        "precio_unitario": "precio_unitario",
        "descuento": "descuento",
        "total_linea": "total_linea",
    },
}


def _stats_vacio(leidos: int) -> dict[str, int]:
    return {
        "leidos": leidos,
        "insertados": 0,
        "actualizados": 0,
        "con_error": 0,
    }


def _serializar_ids_grupo(ids: list | None) -> str | None:
    """Convierte la lista de IDs de origen a string para almacenar en TEXT."""
    if ids is None:
        return None
    return json.dumps(ids, default=str)


class PostgresLoader:
    """Carga en PostgreSQL el resultado de la etapa de Transform."""

    def __init__(self, config: PostgresConfig | None = None):
        self.config = config or get_postgres_config()
        self.queries = _parsear_queries(QUERIES_PATH)
        self.conn = None

    # ---------------------------------------------------------
    # Conexión
    # ---------------------------------------------------------
    def conectar(self):
        """Crea (o reutiliza) la conexión a PostgreSQL."""
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

        Si falla, revierte SOLO esa fila (no toda la transacción) y
        vuelve a lanzar la excepción para que el llamador la cuente
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
            cur.execute("RELEASE SAVEPOINT sp_fila")
            raise

    def _registrar_error(self, cur, tabla: str, identificador: Any, mensaje: str, registro: dict) -> None:
        """Guarda un error de inserción en etl_carga_errores y lo loguea."""
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
            cur.execute("ROLLBACK TO SAVEPOINT sp_error")
            cur.execute("RELEASE SAVEPOINT sp_error")
            logger.error("No se pudo registrar el error de carga en la BD: %s", exc)

    # ---------------------------------------------------------
    # Carga por tabla
    # ---------------------------------------------------------
    def _cargar_clientes(self, clientes: list[dict]) -> tuple[dict, dict]:
        """Inserta/actualiza clientes. Devuelve (stats, mapa_ids) donde
        mapa_ids traduce id_cliente_origen -> id_cliente (serial de Postgres),
        necesario después para resolver la FK de facturas."""
        mapa_campos = COLUMN_MAP["clientes"]
        query = self.queries["upsert_cliente"]
        stats = _stats_vacio(len(clientes))
        mapa_ids: dict[Any, int] = {}

        cur = self.conn.cursor()
        for i, c in enumerate(clientes, start=1):
            id_origen = c.get(mapa_campos["id_cliente_origen"])
            params = {}
            for destino, origen in mapa_campos.items():
                valor = c.get(origen)
                if destino == "ids_origen_grupo":
                    valor = _serializar_ids_grupo(valor)
                params[destino] = valor
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                for id_grupo in c.get("ids_origen_grupo", [id_origen]):
                    mapa_ids[id_grupo] = nuevo_id
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "clientes", params.get("documento", id_origen), str(exc), c)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats, mapa_ids

    def _cargar_productos(self, productos: list[dict]) -> tuple[dict, dict]:
        """Inserta/actualiza productos. Devuelve (stats, mapa_ids)."""
        mapa_campos = COLUMN_MAP["productos"]
        query = self.queries["upsert_producto"]
        stats = _stats_vacio(len(productos))
        mapa_ids: dict[Any, int] = {}

        cur = self.conn.cursor()
        for i, p in enumerate(productos, start=1):
            id_origen = p.get(mapa_campos["id_producto_origen"])
            params = {}
            for destino, origen in mapa_campos.items():
                valor = p.get(origen)
                if destino == "ids_origen_grupo":
                    valor = _serializar_ids_grupo(valor)
                params[destino] = valor
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                for id_grupo in p.get("ids_origen_grupo", [id_origen]):
                    mapa_ids[id_grupo] = nuevo_id
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "productos", params.get("codigo_producto", id_origen), str(exc), p)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats, mapa_ids

    def _cargar_facturas(self, facturas: list[dict], mapa_ids_clientes: dict) -> tuple[dict, dict]:
        """Inserta/actualiza facturas, resolviendo id_cliente_origen ->
        id_cliente (Postgres) con el mapa que devolvió _cargar_clientes."""
        mapa_campos = COLUMN_MAP["facturas"]
        query = self.queries["upsert_factura"]
        stats = _stats_vacio(len(facturas))
        mapa_ids: dict[int, int] = {}

        cur = self.conn.cursor()
        for i, f in enumerate(facturas, start=1):
            id_factura_origen = f.get(mapa_campos["id_factura_origen"])
            numero_factura = f.get(mapa_campos["numero_factura"])
            id_cliente_origen = f.get(mapa_campos["id_cliente_origen"])
            id_cliente_pg = mapa_ids_clientes.get(id_cliente_origen)

            if id_cliente_pg is None:
                stats["con_error"] += 1
                self._registrar_error(
                    cur, "facturas", numero_factura,
                    f"Cliente origen {id_cliente_origen!r} no fue cargado previamente "
                    "(revisar deduplicación/reasignación de FKs en Transform)",
                    f,
                )
                continue

            params = {
                "id_factura_origen": id_factura_origen,
                "numero_factura": numero_factura,
                "id_cliente_origen": id_cliente_origen,
                "id_cliente": id_cliente_pg,
                "fecha_emision": f.get(mapa_campos["fecha_emision"]),
                "estado": f.get(mapa_campos["estado"]),
                "subtotal": f.get(mapa_campos["subtotal"]),
                "iva": f.get(mapa_campos["iva"]),
                "total": f.get(mapa_campos["total"]),
            }
            try:
                nuevo_id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
                mapa_ids[id_factura_origen] = nuevo_id
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
        id_producto y id_factura_origen -> id_factura."""
        mapa_campos = COLUMN_MAP["detalles"]
        query = self.queries["upsert_detalle"]
        stats = _stats_vacio(len(detalles))

        cur = self.conn.cursor()
        for i, d in enumerate(detalles, start=1):
            id_detalle_origen = d.get(mapa_campos["id_detalle_origen"])
            id_factura_origen = d.get(mapa_campos["id_factura_origen"])
            id_producto_origen = d.get(mapa_campos["id_producto_origen"])
            id_factura_pg = mapa_ids_facturas.get(id_factura_origen)
            id_producto_pg = mapa_ids_productos.get(id_producto_origen)

            if id_factura_pg is None or id_producto_pg is None:
                stats["con_error"] += 1
                self._registrar_error(
                    cur, "detalles", f"{id_factura_origen}/{id_producto_origen}",
                    f"No se pudo resolver factura (encontrada={id_factura_pg is not None}) "
                    f"o producto (encontrado={id_producto_pg is not None}) para este detalle",
                    d,
                )
                continue

            params = {
                "id_detalle_origen": id_detalle_origen,
                "id_factura_origen": id_factura_origen,
                "id_factura": id_factura_pg,
                "id_producto_origen": id_producto_origen,
                "id_producto": id_producto_pg,
                "cantidad": d.get(mapa_campos["cantidad"]),
                "precio_unitario": d.get(mapa_campos["precio_unitario"]),
                "descuento": d.get(mapa_campos["descuento"], 0),
                "total_linea": d.get(mapa_campos["total_linea"]),
            }
            try:
                _id, fue_insertado = self._ejecutar_con_savepoint(cur, query, params)
                stats["insertados" if fue_insertado else "actualizados"] += 1
            except psycopg2.Error as exc:
                stats["con_error"] += 1
                self._registrar_error(cur, "detalles", f"{id_factura_origen}/{id_producto_origen}", str(exc), d)
            if i % BATCH_SIZE == 0:
                self.conn.commit()
        self.conn.commit()
        cur.close()
        return stats

    def _cargar_mapeos_y_consolidaciones(self, clientes: list[dict], mapa_ids_clientes: dict) -> dict:
        """Registra la trazabilidad de cada ID de origen y la auditoría de
        los grupos que fueron consolidados en un cliente maestro."""
        stats = _stats_vacio(sum(len(c.get("ids_origen_grupo", [])) for c in clientes))
        cur = self.conn.cursor()
        for cliente in clientes:
            id_sobreviviente = cliente["id_cliente_origen_sobreviviente"]
            id_cliente_pg = mapa_ids_clientes.get(id_sobreviviente)
            if id_cliente_pg is None:
                stats["con_error"] += len(cliente.get("ids_origen_grupo", []))
                continue

            for id_origen in cliente.get("ids_origen_grupo", [id_sobreviviente]):
                cur.execute(
                    self.queries["upsert_cliente_mapeo"],
                    {
                        "id_cliente_origen": id_origen,
                        "id_cliente_sobreviviente": id_sobreviviente,
                        "id_cliente": id_cliente_pg,
                        "es_sobreviviente": id_origen == id_sobreviviente,
                    },
                )
                stats["actualizados"] += 1

            ids_grupo = cliente.get("ids_origen_grupo", [id_sobreviviente])
            if len(ids_grupo) > 1:
                cur.execute(
                    self.queries["upsert_auditoria_consolidacion"],
                    {
                        "id_cliente_sobreviviente": id_sobreviviente,
                        "id_cliente": id_cliente_pg,
                        "ids_origen_grupo": json.dumps(ids_grupo),
                        "cantidad_registros": len(ids_grupo),
                        "datos_maestro": json.dumps(cliente, default=str, ensure_ascii=False),
                    },
                )
        self.conn.commit()
        cur.close()
        return stats

    def _cargar_errores_transformacion(self, errores: list[dict]) -> dict:
        """Persiste los problemas de calidad detectados durante Transform.
        Son datos auditables, no fallos técnicos de la carga."""
        stats = _stats_vacio(len(errores))
        cur = self.conn.cursor()
        for error in errores:
            try:
                cur.execute("SAVEPOINT sp_error_transformacion")
                cur.execute(
                    self.queries["upsert_error_transformacion"],
                    {
                        "entidad": error.get("entidad", "desconocida"),
                        "id_origen": error.get("id_origen"),
                        "campo": error.get("campo", "desconocido"),
                        "valor_original": None if error.get("valor_original") is None else str(error.get("valor_original")),
                        "motivo": error.get("motivo", "Sin detalle"),
                    },
                )
                cur.execute("RELEASE SAVEPOINT sp_error_transformacion")
                stats["actualizados"] += 1
            except psycopg2.Error as exc:
                cur.execute("ROLLBACK TO SAVEPOINT sp_error_transformacion")
                cur.execute("RELEASE SAVEPOINT sp_error_transformacion")
                stats["con_error"] += 1
                self._registrar_error(cur, "errores_transformacion", error.get("id_origen"), str(exc), error)
        self.conn.commit()
        cur.close()
        return stats

    def _validar_destino(self, resultado_transformado: dict) -> dict:
        """Compara cantidades, total monetario e integridad referencial.
        Registra cada comprobación y falla si una validación crítica no coincide."""
        esperados = {
            "clientes": len(resultado_transformado.get("clientes", [])),
            "productos": len(resultado_transformado.get("productos", [])),
            "facturas": len(resultado_transformado.get("facturas", [])),
            "detalles": len(resultado_transformado.get("detalles", [])),
        }
        total_esperado = round(sum(float(f.get("total") or 0) for f in resultado_transformado.get("facturas", [])), 2)

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM clientes")
        clientes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM productos")
        productos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM facturas")
        facturas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM detalles")
        detalles = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(total), 0) FROM facturas")
        total_destino = round(float(cur.fetchone()[0]), 2)
        cur.execute("SELECT COUNT(*) FROM facturas f LEFT JOIN clientes c ON c.id_cliente=f.id_cliente WHERE c.id_cliente IS NULL")
        facturas_huerfanas = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM detalles d LEFT JOIN facturas f ON f.id_factura=d.id_factura WHERE f.id_factura IS NULL")
        detalles_sin_factura = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM detalles d LEFT JOIN productos p ON p.id_producto=d.id_producto WHERE p.id_producto IS NULL")
        detalles_sin_producto = cur.fetchone()[0]

        valores = {
            "clientes": clientes,
            "productos": productos,
            "facturas": facturas,
            "detalles": detalles,
        }
        resultados = []
        for nombre, esperado in esperados.items():
            real = valores[nombre]
            resultados.append((f"cantidad_{nombre}", esperado, real, esperado == real, "Comparación de cantidades"))
        resultados.append(("total_facturado", total_esperado, total_destino, abs(total_esperado-total_destino) <= 0.01, "Comparación monetaria"))
        resultados.extend([
            ("facturas_sin_cliente", 0, facturas_huerfanas, facturas_huerfanas == 0, "Integridad FK cliente"),
            ("detalles_sin_factura", 0, detalles_sin_factura, detalles_sin_factura == 0, "Integridad FK factura"),
            ("detalles_sin_producto", 0, detalles_sin_producto, detalles_sin_producto == 0, "Integridad FK producto"),
        ])

        for nombre, origen, destino, correcto, detalle in resultados:
            cur.execute(
                self.queries["insertar_validacion"],
                {
                    "nombre_validacion": nombre,
                    "valor_origen": origen,
                    "valor_destino": destino,
                    "es_correcto": correcto,
                    "detalle": detalle,
                },
            )
        self.conn.commit()
        cur.close()

        fallidas = [nombre for nombre, _o, _d, correcto, _detalle in resultados if not correcto]
        if fallidas:
            raise RuntimeError("Fallaron validaciones de destino: " + ", ".join(fallidas))

        return {
            "cantidades": valores,
            "total_facturado": total_destino,
            "facturas_sin_cliente": facturas_huerfanas,
            "detalles_sin_factura": detalles_sin_factura,
            "detalles_sin_producto": detalles_sin_producto,
        }

    # ---------------------------------------------------------
    # Estadísticas de carga
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
        (respetando las FKs), y devuelve un resumen de estadísticas.

        Parámetros
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

        t0 = time.time()
        stats_mapeos = self._cargar_mapeos_y_consolidaciones(
            resultado_transformado.get("clientes", []), mapa_ids_clientes
        )
        stats_por_tabla["mapeos_clientes"] = (stats_mapeos, time.time() - t0)

        t0 = time.time()
        stats_errores_transformacion = self._cargar_errores_transformacion(
            resultado_transformado.get("errores", [])
        )
        stats_por_tabla["errores_transformacion"] = (stats_errores_transformacion, time.time() - t0)

        self._guardar_auditoria(stats_por_tabla)
        validacion = self._validar_destino(resultado_transformado)
        self._mostrar_resumen(stats_por_tabla)

        resumen = {tabla: stats for tabla, (stats, _duracion) in stats_por_tabla.items()}
        resumen["validacion"] = validacion
        return resumen


# ----------------------------------------------------------------
# Ejecución standalone: útil para probar solo la etapa de Load,
# reutilizando el respaldo JSON que pipeline.py genera cuando esta
# etapa todavía no existía (data/output/resultado_transformado.json).
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
