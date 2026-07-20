USE SmartCleanOrigen;
GO

PRINT N'1. Resumen general';
SELECT * FROM dbo.vw_ResumenBaseOrigen;

PRINT N'2. Indicadores de calidad';
SELECT * FROM dbo.vw_IndicadoresCalidadOrigen;

PRINT N'3. Total monetario';
SELECT * FROM dbo.vw_TotalVentasOrigen;

PRINT N'4. Integridad referencial';
SELECT * FROM dbo.vw_IntegridadOrigen;

PRINT N'5. Clientes potencialmente duplicados';
SELECT *
FROM dbo.vw_ClientesPotencialmenteDuplicados
ORDER BY PuntajeSugerido DESC, IdClienteA, IdClienteB;

PRINT N'6. Registros con inconsistencias';
SELECT
    IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
    FechaNacimientoTexto, FechaRegistroTexto,
    CorreoInvalido, TelefonoInvalido, DocumentoInvalido,
    FechaNacimientoInvalida, FechaRegistroInvalida
FROM dbo.vw_DatosInconsistentesCliente
WHERE CorreoInvalido = 1
   OR TelefonoInvalido = 1
   OR DocumentoInvalido = 1
   OR FechaNacimientoInvalida = 1
   OR FechaRegistroInvalida = 1
ORDER BY IdClienteOrigen;

PRINT N'7. Facturas de los tres registros del cliente Juan Pérez';
SELECT *
FROM dbo.vw_FacturasConCliente
WHERE IdClienteOrigen IN (1, 2, 3)
ORDER BY IdFacturaOrigen;

PRINT N'8. Últimas ejecuciones de carga';
SELECT TOP (10) *
FROM dbo.CargaOrigenLog
ORDER BY IdCarga DESC;

PRINT N'9. Errores registrados';
SELECT TOP (10) *
FROM dbo.CargaOrigenError
ORDER BY IdError DESC;
GO
