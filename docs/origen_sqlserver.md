# Módulo de origen SQL Server — SmartClean Clientes

## Alcance

La base `SmartCleanOrigen` contiene:

- **1.200 clientes de origen**.
- 60 productos.
- 1.206 facturas.
- 2.412 detalles.
- Total facturado: **120.011,78**.
- Duplicados, espacios, mayúsculas inconsistentes, correos inválidos,
  teléfonos incompletos, documentos nulos/formateados y fechas no convertibles.

El grupo de Juan Pérez corresponde a los IDs 1, 2 y 3. Sus nueve facturas permiten demostrar que la consolidación no pierde el historial.

## Elementos académicos implementados

- `dbo.sp_CargarDatosOrigenJson` con `OPENJSON`.
- `TRY/CATCH`, `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK` y `THROW`.
- Carga repetible con `MERGE`.
- Registro técnico en `CargaOrigenLog` y `CargaOrigenError`.
- Vistas de resumen, integridad, calidad y duplicados.
- Índices sobre documentos, correos, teléfonos y claves foráneas.

## Ejecución

```bash
docker compose down -v
docker compose up -d --build sqlserver
docker compose logs -f sqlserver
```

Cuando aparezca `Base SmartCleanOrigen inicializada correctamente`:

```bash
docker compose exec sqlserver bash -lc '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -d SmartCleanOrigen -Q "SELECT * FROM dbo.vw_ResumenBaseOrigen; SELECT * FROM dbo.vw_IntegridadOrigen; SELECT * FROM dbo.vw_IndicadoresCalidadOrigen;"'
```

## Conexiones

Desde Windows:

- Servidor: `localhost,1435`
- Usuario: `sa`
- Contraseña: valor de `MSSQL_SA_PASSWORD`
- Base: `SmartCleanOrigen`

Desde otro contenedor:

- Host: `sqlserver`
- Puerto: `1433`

## Regenerar el JSON

```bash
python data/generate_dirty_data.py
```

El generador es determinista y vuelve a producir las cantidades documentadas.
