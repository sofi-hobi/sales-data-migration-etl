# Sales Data Migration ETL — SQL Server → PostgreSQL

Pipeline ETL de migración heterogénea que extrae datos "sucios" desde SQL Server, los limpia/deduplica/fusiona en Python, y los carga en PostgreSQL.

## Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐      ┌─────────────────┐
│   SQL Server    │     │   Python ETL     │     │   PostgreSQL    │      │    Web App      │
│  (Origen)       │────▶│                  │────▶│  (Destino)      │      │ (Demostración)  │
│                 │     │  Extract         │     │                 │      │                 │
│ SmartCleanOrigen│     │  Transform       │     │  etl_destino    │      │ UI con pestañas │
│ - ClienteOrigen │     │  Load            │     │  - clientes     │      │ para comparar:  │
│ - ProductoOrigen│     │                  │     │  - productos    │      │ SQL vs Postgres │
│ - FacturaOrigen │     │  Limpieza        │     │  - facturas     │◀─────│                 │
│ - DetalleOrigen │     │  Deduplicación   │     │  - detalles     │      │ (localhost:8000)│
│                 │     │  Survivorship    │     │  - auditoría    │      │                 │
│ (datos sucios)  │     │  Validación      │     │  (datos limpios)│      │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘      └─────────────────┘
```

## Requisitos

- Docker y Docker Compose v2+

## Inicio rápido y Manejo de Docker

Debido a que SQL Server inicializa su base de datos desde cero usando scripts, **siempre debes limpiar los volúmenes antiguos** antes de levantar el proyecto. Si no lo haces, SQL Server fallará intentando recuperar la base de datos vieja.

```bash
# 1. (Opcional) Crear archivo .env si no existe
cp .env.example .env

# 2. Detener contenedores y LIMPIAR volúmenes (¡Obligatorio para reiniciar!)
docker compose down -v

# 3. Levantar todos los servicios en segundo plano
docker compose up -d --build
```

Una vez levantado:

- El **Pipeline ETL** se ejecutará automáticamente para limpiar y migrar los datos.
- Puedes ver la **Página Web de Demostración** entrando a: 👉 **<http://localhost:8000>**

Para detener el proyecto al terminar:

```bash
docker compose down
```

## Verificar resultados

```bash
# Ver las tablas cargadas en PostgreSQL
docker compose exec postgres psql -U etl_user -d etl_destino -c "
  SELECT 'clientes' AS tabla, count(*) FROM clientes
  UNION ALL SELECT 'productos', count(*) FROM productos
  UNION ALL SELECT 'facturas', count(*) FROM facturas
  UNION ALL SELECT 'detalles', count(*) FROM detalles;
"

# Ver estadísticas de la carga
docker compose exec postgres psql -U etl_user -d etl_destino -c "
  SELECT * FROM etl_carga_auditoria ORDER BY id_carga;
"

# Verificar datos en SQL Server de origen
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "Grupo1@BDD!" -C \
  -d SmartCleanOrigen \
  -Q "SELECT * FROM dbo.vw_ResumenBaseOrigen;"
```

## Estructura del proyecto

```
sales-data-migration-etl/
├── docker-compose.yml          # Orquesta los 4 servicios
├── Dockerfile                  # Imagen del pipeline ETL (Python + ODBC)
├── requirements.txt            # Dependencias Python del pipeline
├── .env.example                # Variables de entorno de ejemplo
│
├── webapp/                     # Web App interactiva de demostración
│   ├── main.py                 # Backend FastAPI
│   ├── requirements.txt        # Dependencias web
│   ├── Dockerfile
│   └── static/
│       └── index.html          # Interfaz UI con glassmorphism
├── sqlserver/                  # Contenedor SQL Server (origen)
│   ├── Dockerfile
│   ├── entrypoint.sh           # Espera SQL Server → ejecuta scripts
│   └── scripts.sql             # Orquesta la ejecución de source_schema/
│
├── postgres/                   # Contenedor PostgreSQL (destino)
│   ├── Dockerfile
│   ├── 001_postgres_ddl.sql    # Tablas de negocio (clientes, productos, etc.)
│   └── 002_audit_tables.sql    # Tablas de auditoría de carga
│
├── sql/
│   └── source_schema/          # DDL del origen SQL Server
│       ├── 01_create_tables.sql
│       ├── 02_create_procedures.sql
│       ├── 03_create_views.sql
│       ├── 04_load_json.sql
│       └── 05_validation_queries.sql
│
├── data/
│   └── source/
│       └── datos_origen.json   # Datos semilla (20 clientes sucios, etc.)
│
├── src/                        # Código Python del pipeline ETL
│   ├── pipeline.py             # Punto de entrada: Extract → Transform → Load
│   ├── config/
│   │   ├── settings.py         # Configuración centralizada (env vars)
│   │   └── logging_config.py
│   ├── extract/
│   │   └── sqlserver_connector.py   # Lee datos crudos de SQL Server
│   ├── transform/
│   │   ├── orchestrator.py     # Orquesta limpieza → dedup → survivorship
│   │   ├── cleansing.py        # Normalización de campos
│   │   ├── deduplication.py    # Union-Find para detectar duplicados
│   │   ├── survivorship.py     # Elige registro sobreviviente
│   │   ├── fk_reassignment.py  # Reasigna FKs al sobreviviente
│   │   └── validation.py       # Validaciones de formato y negocio
│   └── load/
│       ├── postgres_connector.py  # Carga datos en PostgreSQL (UPSERT)
│       └── load_queries.sql       # Consultas SQL parametrizadas
│
├── tests/                      # Tests unitarios e integración
│   ├── unit/
│   └── integration/
│
└── docs/
    └── origen_sqlserver.md     # Documentación del módulo origen
```

## Pipeline ETL — Detalle de cada etapa

### 1. Extract (SQL Server → Python)

Conecta a SQL Server vía pyodbc y extrae las 4 tablas de origen como listas de diccionarios, sin modificar los datos.

### 2. Transform (Limpieza + Deduplicación)

1. **Cleansing**: Normaliza nombres (Title Case), limpia espacios, valida correos, estandariza teléfonos, parsea fechas
2. **Deduplication**: Algoritmo Union-Find que agrupa registros por documento/correo coincidente
3. **Survivorship**: Elige el registro más completo como "sobreviviente", fusiona campos faltantes desde los duplicados
4. **FK Reassignment**: Reasigna las llaves foráneas de facturas y detalles para que apunten al sobreviviente
5. **Validation**: Detecta errores de formato e inconsistencias de negocio (totales que no cuadran, fechas futuras, etc.)

### 3. Load (Python → PostgreSQL)

Inserta los datos limpios en PostgreSQL usando UPSERT (`INSERT ... ON CONFLICT ... DO UPDATE`). Cada fila se ejecuta dentro de un SAVEPOINT para que un error no tumbe toda la transacción. Registra estadísticas en `etl_carga_auditoria` y errores en `etl_carga_errores`.

## Conexiones locales

| Base | Host | Puerto | Usuario | Contraseña | Base de datos |
|---|---|---|---|---|---|
| SQL Server | `localhost` | `1435` | `sa` | `Grupo1@BDD!` | `SmartCleanOrigen` |
| PostgreSQL | `localhost` | `5432` | `etl_user` | `Grupo1_PG!` | `etl_destino` |

## Reejecutar solo el pipeline (Sin reiniciar BD)

Si modificaste el código Python en `src/` y solo quieres probar el ETL sin tener que borrar y recrear las bases de datos de nuevo, corre:

```bash
# Vuelve a compilar y ejecutar solo el contenedor de ETL
docker compose build etl_pipeline
docker compose up etl_pipeline
```

## Demostración en vivo

1. Asegúrate de tener la aplicación levantada y muestra la web en `http://localhost:8000`.
2. Ejecuta este comando en tu terminal para inyectar nuevos datos JSON sucios/limpios "en caliente" directamente a SQL Server sin tener que apagar los contenedores:

   ```bash
   docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Grupo1@BDD!" -C -d SmartCleanOrigen -i /usr/src/app/source_schema/06_load_live_demo.sql
   ```

3. Ahora ejecuta el pipeline ETL para que limpie y migre esos nuevos datos:

   ```bash
   docker compose run --rm etl_pipeline
   ```

4. Refresca tu página web y verás cómo los datos válidos ("Cliente Super Nuevo") aparecieron en PostgreSQL, mientras que los datos sucios ("Cliente Malo Demo") fueron rechazados y filtrados.

## Tests

```bash
# Ejecutar tests unitarios (no requieren Docker)
pip install pyodbc psycopg2-binary
python -m pytest tests/unit/ -v
```
