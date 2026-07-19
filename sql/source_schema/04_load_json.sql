USE SmartCleanOrigen;
GO

DECLARE @DatosJson NVARCHAR(MAX);

-- SQL Server ejecutado en Linux no admite la opción CODEPAGE en OPENROWSET(BULK).
-- El archivo JSON se guarda usando escapes Unicode (\uXXXX), por lo que puede
-- leerse de forma segura como SINGLE_CLOB sin perder tildes ni caracteres especiales.
SELECT @DatosJson = CONVERT(NVARCHAR(MAX), BulkColumn)
FROM OPENROWSET
(
    BULK '/usr/src/app/data/datos_origen.json',
    SINGLE_CLOB
) AS archivo;

IF ISJSON(@DatosJson) <> 1
BEGIN
    THROW 51001, N'El archivo datos_origen.json no contiene un JSON válido.', 1;
END;

EXEC dbo.sp_CargarDatosOrigenJson
    @DatosJson = @DatosJson,
    @ArchivoOrigen = N'/usr/src/app/data/datos_origen.json',
    @Reiniciar = 1;
GO

SELECT * FROM dbo.vw_ResumenBaseOrigen;
SELECT * FROM dbo.vw_TotalVentasOrigen;
SELECT * FROM dbo.vw_IntegridadOrigen;
GO
