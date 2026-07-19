# deduplication.py
"""Deteccion de registros duplicados usando Union-Find sobre llaves normalizadas."""
from __future__ import annotations

from collections import defaultdict


class UnionFind:
    def __init__(self, elementos):
        self._padre = {elemento: elemento for elemento in elementos}

    def encontrar(self, x):
        while self._padre[x] != x:
            self._padre[x] = self._padre[self._padre[x]]
            x = self._padre[x]
        return x

    def unir(self, a, b):
        raiz_a, raiz_b = self.encontrar(a), self.encontrar(b)
        if raiz_a != raiz_b:
            self._padre[raiz_a] = raiz_b

    def grupos(self):
        agrupados = defaultdict(list)
        for elemento in self._padre:
            agrupados[self.encontrar(elemento)].append(elemento)
        return list(agrupados.values())


def _indexar(indice, clave, id_registro):
    if clave:
        indice.setdefault(clave, []).append(id_registro)


def agrupar_duplicados_clientes(clientes_limpios):
    ids = [c["id_cliente_origen"] for c in clientes_limpios]
    uf = UnionFind(ids)

    por_documento, por_correo = {}, {}
    for cliente in clientes_limpios:
        _indexar(por_documento, cliente["documento"], cliente["id_cliente_origen"])
        _indexar(por_correo, cliente["correo"], cliente["id_cliente_origen"])

    for indice in (por_documento, por_correo):
        for ids_coincidentes in indice.values():
            for otro in ids_coincidentes[1:]:
                uf.unir(ids_coincidentes[0], otro)

    return uf.grupos()


def agrupar_duplicados_productos(productos_limpios):
    ids = [p["id_producto_origen"] for p in productos_limpios]
    uf = UnionFind(ids)

    por_codigo = {}
    for producto in productos_limpios:
        codigo = (producto["codigo_producto"] or "").upper() or None
        _indexar(por_codigo, codigo, producto["id_producto_origen"])

    for ids_coincidentes in por_codigo.values():
        for otro in ids_coincidentes[1:]:
            uf.unir(ids_coincidentes[0], otro)

    return uf.grupos()
