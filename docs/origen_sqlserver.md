# Módulo de origen SQL Server — SmartClean Clientes

## Alcance

Este módulo crea la base `SmartCleanOrigen` con:

- 20 clientes de origen.
- 12 productos.
- 30 facturas.
- 66 detalles de factura.
- Datos intencionalmente sucios: duplicados, espacios, mayúsculas inconsistentes,
  correos inválidos, teléfonos incompletos y fechas no convertibles.
- Procedimiento `dbo.sp_CargarDatosOrigenJson`.
- Carga idempotente mediante `MERGE`.
- `TRY/CATCH`, transacción, `COMMIT`, `ROLLBACK` y registro de errores.
- Vistas de resumen, integridad, inconsistencias y duplicados probables.

El grupo de Juan Pérez corresponde a los identificadores 1, 2 y 3. Entre los tres
poseen nueve facturas, lo que permite demostrar posteriormente la consolidación
sin pérdida del historial.

## Ejecución

Desde la raíz del repositorio:

```bash
docker compose down -v
docker compose up -d --build sqlserver
docker compose logs -f sqlserver
```

Cuando aparezca `Base SmartCleanOrigen inicializada correctamente`, verificar:

```bash
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd   -S localhost -U sa -P "Grupo1@BDD!" -C   -d SmartCleanOrigen   -Q "SELECT * FROM dbo.vw_ResumenBaseOrigen; SELECT * FROM dbo.vw_IntegridadOrigen;"
```

Conexión desde Windows:

- Servidor: `localhost,1435`
- Usuario: `sa`
- Contraseña: `Grupo1@BDD!`
- Base: `SmartCleanOrigen`

Conexión desde otro contenedor de Compose:

- Host: `sqlserver`
- Puerto: `1433`
- Usuario: `sa`
- Contraseña: la variable `MSSQL_SA_PASSWORD`
- Base: `SmartCleanOrigen`

## Reejecución

El procedimiento usa `MERGE`, por lo que se puede ejecutar nuevamente sin
duplicar claves. El script inicial usa `@Reiniciar = 1` para que cada creación
del contenedor produzca un escenario determinista.

## Resultados esperados

| Métrica | Valor |
|---|---:|
| Clientes | 20 |
| Productos | 12 |
| Facturas | 30 |
| Detalles | 66 |
| Total facturado | 1045.06 |
| Facturas sin cliente | 0 |
| Detalles sin factura | 0 |
| Detalles sin producto | 0 |
