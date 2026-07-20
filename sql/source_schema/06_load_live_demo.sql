USE SmartCleanOrigen;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

PRINT N'Cargando nuevo JSON en vivo...';

DECLARE @json NVARCHAR(MAX);

-- Leemos el nuevo archivo JSON
SELECT @json = CONVERT(NVARCHAR(MAX), BulkColumn)
FROM OPENROWSET(BULK '/usr/src/app/data/datos_live_demo.json', SINGLE_CLOB) AS J;

-- Ejecutamos el procedimiento almacenado pasando el parametro @Reiniciar = 0 (hace un UPSERT sin borrar lo anterior)
EXEC dbo.sp_CargarDatosOrigenJson 
    @DatosJson = @json, 
    @ArchivoOrigen = N'datos_live_demo.json', 
    @Reiniciar = 0;

PRINT N'¡Carga de datos nuevos finalizada!';
GO
