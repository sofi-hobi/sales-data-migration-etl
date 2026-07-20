# Correcciones realizadas y contrato de ejecución

Esta versión corrige la integración completa del proyecto **SmartClean Clientes** y amplía el origen a más de mil clientes.

## Dataset final

| Entidad | SQL Server (origen) | PostgreSQL (destino esperado) |
|---|---:|---:|
| Clientes | 1.200 | 1.098 clientes maestros |
| Productos | 60 | 55 productos maestros |
| Facturas | 1.206 | 1.206 |
| Detalles | 2.412 | 2.412 |
| Total facturado | 120.011,78 | 120.011,78 |

Se generan 101 grupos de clientes duplicados y se consolidan 102 filas repetidas. Los clientes de origen 1, 2 y 3 corresponden a variantes de Juan Pérez; sus nueve facturas se reasignan al mismo cliente maestro.

## Correcciones principales

1. **Inicialización de SQL Server**
   - Se crea `SmartCleanOrigen` solo cuando no existe.
   - Se eliminó el `ALTER DATABASE` que fallaba antes de crear la base.
   - El contenedor espera a que SQL Server acepte conexiones antes de ejecutar los scripts.
   - El healthcheck valida la tabla de clientes y exige al menos 1.000 registros.

2. **Carga del origen desde JSON**
   - Se agregó un generador reproducible: `data/generate_dirty_data.py`.
   - El JSON se guarda con escapes Unicode para ser compatible con `SINGLE_CLOB` en SQL Server Linux.
   - La carga utiliza `OPENJSON`, `TRY/CATCH`, transacción, `COMMIT`, `ROLLBACK` y `MERGE`.
   - El procedimiento rechaza una carga inicial con menos de 1.000 clientes.

3. **Transformación**
   - Se preservan los estados reales de factura (`PAGADA`, `PENDIENTE`, `ANULADA`, etc.).
   - Los teléfonos cortos o inválidos ya no provocan falsos duplicados.
   - Los productos se deduplican con código normalizado.
   - Se valida que no se pierdan facturas, detalles ni total monetario.

4. **Carga a PostgreSQL**
   - Los UPSERT usan identificadores estables del origen.
   - Se conserva a clientes sin documento.
   - Cada detalle se identifica por `id_detalle_origen`, evitando perder líneas repetidas del mismo producto.
   - Se añadieron mapeo de clientes, auditoría de consolidación, errores de calidad y resultados de validación.
   - Los SAVEPOINT se liberan también después de un rollback de fila.

5. **Docker e interfaz web**
   - El ETL espera a que ambas bases estén saludables.
   - La web inicia únicamente después de que el ETL termina correctamente.
   - El healthcheck web usa consultas `SELECT 1` ligeras.
   - La API muestra errores explícitos y limita la muestra a 100 filas por tabla.

## Prueba limpia en Windows / Git Bash

```bash
cp .env.example .env
docker compose down -v
docker compose up -d --build
docker compose ps -a
```

Abrir:

```text
http://localhost:8000
```

Estados esperados:

- `sqlserver`: healthy
- `postgres`: healthy
- `etl_pipeline`: Exited (0)
- `webapp`: healthy o running

## Verificación de cantidades

```bash
docker compose exec sqlserver bash -lc '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -d SmartCleanOrigen -Q "SELECT * FROM dbo.vw_ResumenBaseOrigen; SELECT * FROM dbo.vw_IntegridadOrigen;"'
```

```bash
docker compose exec postgres psql -U etl_user -d etl_destino -c "
SELECT 'clientes' AS tabla, COUNT(*) AS cantidad FROM clientes
UNION ALL SELECT 'productos', COUNT(*) FROM productos
UNION ALL SELECT 'facturas', COUNT(*) FROM facturas
UNION ALL SELECT 'detalles', COUNT(*) FROM detalles;
"
```

## Reejecución idempotente

```bash
docker compose run --rm etl_pipeline
```

La segunda ejecución debe conservar las mismas cantidades de negocio; los registros se actualizan mediante UPSERT y no se duplican.
