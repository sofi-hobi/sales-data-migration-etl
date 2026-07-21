# SmartClean Clientes — Migración SQL Server → PostgreSQL

Proyecto ETL heterogéneo que extrae una base de ventas con datos sucios desde **SQL Server**, normaliza y consolida clientes/productos en **Python**, y carga el resultado limpio en **PostgreSQL**. Todo se ejecuta con Docker Compose y puede demostrarse en una aplicación web.
> **Guía detallada para el docente:** consulte [`docs/GUIA_EJECUCION.md`](docs/GUIA_EJECUCION.md) o [`docs/GUIA_EJECUCION.pdf`](docs/GUIA_EJECUCION.pdf).


## Arquitectura

```text
JSON sucio → SQL Server (origen) → Extract → Transform → Load → PostgreSQL (destino)
                                              ↓
                                      auditoría y validaciones
                                              ↓
                                      Web http://localhost:8000
```

El flujo respeta la distribución del documento del grupo: origen SQL Server, extracción sin modificar datos, transformación, carga PostgreSQL e integración con Docker. 

## Datos incluidos

| Métrica | Origen SQL Server | Destino PostgreSQL |
|---|---:|---:|
| Clientes | **1.200** | **1.098 maestros** |
| Productos | 60 | 55 maestros |
| Facturas | 1.206 | 1.206 |
| Detalles | 2.412 | 2.412 |
| Total facturado | 120.011,78 | 120.011,78 |

Se incluyen **101 grupos de clientes duplicados** y 102 registros que se consolidan. Los clientes 1, 2 y 3 representan a Juan Pérez; sus nueve facturas se reasignan al mismo cliente maestro sin perder historial.

## Requisitos

- Docker Desktop con el motor WSL 2 activo.
- Docker Compose v2 o superior.
- Puertos libres: `1435`, `5432` y `8000`.

## Ejecución limpia

Desde la raíz del proyecto:

```bash
cp .env.example .env
docker compose down -v --remove-orphans
docker compose up -d --build
```

La primera construcción puede tardar porque descarga SQL Server, PostgreSQL, Python y el driver ODBC.

Verifica el estado:

```bash
docker compose ps -a
```

Resultado normal:

- `sqlserver`: `healthy`
- `postgres`: `healthy`
- `etl_pipeline`: `Exited (0)`
- `webapp`: `healthy` o `running`

Abre la demostración:

```text
http://localhost:8000
```

La web muestra las cantidades totales y una muestra de 100 filas por tabla para evitar cargar miles de registros en el navegador.

## Verificaciones rápidas

### SQL Server

```bash
docker compose exec sqlserver bash -lc '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -d SmartCleanOrigen -Q "SELECT * FROM dbo.vw_ResumenBaseOrigen; SELECT * FROM dbo.vw_IntegridadOrigen; SELECT * FROM dbo.vw_IndicadoresCalidadOrigen;"'
```

### PostgreSQL

```bash
docker compose exec postgres psql -U etl_user -d etl_destino -c "
SELECT 'clientes' tabla, COUNT(*) cantidad FROM clientes
UNION ALL SELECT 'productos', COUNT(*) FROM productos
UNION ALL SELECT 'facturas', COUNT(*) FROM facturas
UNION ALL SELECT 'detalles', COUNT(*) FROM detalles;
"
```

Auditoría y trazabilidad:

```bash
docker compose exec postgres psql -U etl_user -d etl_destino -c "
SELECT COUNT(*) AS mapeos FROM cliente_origen_mapeo;
SELECT COUNT(*) AS grupos_consolidados FROM auditoria_consolidacion;
SELECT COUNT(*) AS errores_calidad FROM etl_transformacion_errores;
SELECT * FROM etl_validacion_resultado ORDER BY id_validacion DESC LIMIT 10;
"
```

## Reejecución sin duplicar

Con las bases levantadas:

```bash
docker compose run --rm etl_pipeline
```

Los UPSERT se realizan usando los identificadores estables del origen. Una segunda ejecución actualiza las filas existentes y conserva las cantidades.

Cuando se modifiquen los scripts de creación de PostgreSQL, usa una prueba limpia porque los archivos de `/docker-entrypoint-initdb.d` solo se ejecutan al crear el volumen:

```bash
docker compose down -v --remove-orphans
docker compose up -d --build
```

## Componentes principales

```text
data/
  generate_dirty_data.py       Generador reproducible de los 1.200 clientes
  source/datos_origen.json     Dataset sucio cargado en SQL Server
sql/source_schema/
  01_create_tables.sql
  02_create_procedures.sql     OPENJSON, TRY/CATCH, COMMIT/ROLLBACK y MERGE
  03_create_views.sql
  04_load_json.sql
postgres/
  001_postgres_ddl.sql         Tablas normalizadas
  002_audit_tables.sql         Mapeos, consolidación, errores y validaciones
src/
  extract/                     Lectura sin transformación
  transform/                   Limpieza, deduplicación, survivorship y FKs
  load/                        UPSERT, auditoría y validación final
webapp/                        FastAPI + interfaz de comparación
```

## Reglas aplicadas

- Colapso de espacios y normalización de nombres.
- Correos en minúsculas y validación de formato.
- Documentos y teléfonos reducidos a dígitos.
- Fechas convertidas desde varios formatos; fechas inválidas se auditan.
- Duplicación por documento, correo o teléfono completo.
- Selección del registro más completo como maestro.
- Reasignación de facturas y productos hacia los sobrevivientes.
- Clientes sin documento se conservan; no se pierden sus facturas.
- Estados de factura (`PAGADA`, `PENDIENTE`, `ANULADA`, etc.) se conservan.
- Validación automática de cantidades, total monetario y referencias huérfanas.

## Pruebas sin Docker

```bash
python -m pip install pytest psycopg2-binary
python -m pytest tests -q
```

El conjunto incluye pruebas unitarias y un contrato integral sobre el dataset de 1.200 clientes.

## Ejecución reproducible para el docente

El proyecto incluye el dataset de origen versionado, variables de entorno de ejemplo, healthchecks y dependencias entre servicios. Para simular una computadora nueva, clone `main` en otra carpeta y ejecute:

```bash
git clone https://github.com/sofi-hobi/sales-data-migration-etl.git prueba-profesor
cd prueba-profesor
cp .env.example .env
docker compose down -v --remove-orphans
docker compose up -d --build
docker compose ps -a
```

Los resultados esperados y las consultas de comprobación están detallados en [`docs/GUIA_EJECUCION.md`](docs/GUIA_EJECUCION.md).

## Diagnóstico

```bash
docker compose logs --tail=200 sqlserver
docker compose logs --tail=200 etl_pipeline
docker compose logs --tail=200 webapp
```

Para generar un archivo de evidencias:

```bash
docker compose logs --no-color > logs_proyecto.txt
```
