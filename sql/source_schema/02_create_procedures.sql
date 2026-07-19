USE SmartCleanOrigen;
GO

CREATE OR ALTER PROCEDURE dbo.sp_CargarDatosOrigenJson
    @DatosJson NVARCHAR(MAX),
    @ArchivoOrigen NVARCHAR(260) = N'datos_origen.json',
    @Reiniciar BIT = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE
        @FechaInicio DATETIME2(0) = SYSUTCDATETIME(),
        @ClientesLeidos INT = 0,
        @ProductosLeidos INT = 0,
        @FacturasLeidas INT = 0,
        @DetallesLeidos INT = 0;

    IF @DatosJson IS NULL OR ISJSON(@DatosJson) <> 1
        THROW 51000, N'El contenido recibido no es un JSON válido.', 1;

    DECLARE @Clientes TABLE
    (
        IdClienteOrigen INT NOT NULL PRIMARY KEY,
        Documento NVARCHAR(30) NULL,
        Nombre NVARCHAR(100) NULL,
        Apellido NVARCHAR(120) NULL,
        Correo NVARCHAR(180) NULL,
        Telefono NVARCHAR(50) NULL,
        Direccion NVARCHAR(250) NULL,
        Ciudad NVARCHAR(100) NULL,
        FechaNacimientoTexto NVARCHAR(30) NULL,
        FechaRegistroTexto NVARCHAR(30) NULL,
        EstadoTexto NVARCHAR(30) NULL
    );

    DECLARE @Productos TABLE
    (
        IdProductoOrigen INT NOT NULL PRIMARY KEY,
        CodigoProducto NVARCHAR(30) NULL,
        NombreProducto NVARCHAR(160) NULL,
        CategoriaTexto NVARCHAR(100) NULL,
        Precio DECIMAL(18,2) NULL,
        EstadoTexto NVARCHAR(30) NULL
    );

    DECLARE @Facturas TABLE
    (
        IdFacturaOrigen INT NOT NULL PRIMARY KEY,
        NumeroFactura NVARCHAR(40) NOT NULL,
        IdClienteOrigen INT NOT NULL,
        FechaEmisionTexto NVARCHAR(30) NULL,
        EstadoTexto NVARCHAR(30) NULL,
        Subtotal DECIMAL(18,2) NOT NULL,
        IVA DECIMAL(18,2) NOT NULL,
        Total DECIMAL(18,2) NOT NULL
    );

    DECLARE @Detalles TABLE
    (
        IdDetalleOrigen INT NOT NULL PRIMARY KEY,
        IdFacturaOrigen INT NOT NULL,
        IdProductoOrigen INT NOT NULL,
        Cantidad INT NOT NULL,
        PrecioUnitario DECIMAL(18,2) NOT NULL,
        Descuento DECIMAL(18,2) NOT NULL,
        TotalLinea DECIMAL(18,2) NOT NULL
    );

    BEGIN TRY
        INSERT INTO @Clientes
        (
            IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
            Direccion, Ciudad, FechaNacimientoTexto, FechaRegistroTexto, EstadoTexto
        )
        SELECT
            IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
            Direccion, Ciudad, FechaNacimientoTexto, FechaRegistroTexto, EstadoTexto
        FROM OPENJSON(@DatosJson, '$.clientes')
        WITH
        (
            IdClienteOrigen INT '$.idClienteOrigen',
            Documento NVARCHAR(30) '$.documento',
            Nombre NVARCHAR(100) '$.nombre',
            Apellido NVARCHAR(120) '$.apellido',
            Correo NVARCHAR(180) '$.correo',
            Telefono NVARCHAR(50) '$.telefono',
            Direccion NVARCHAR(250) '$.direccion',
            Ciudad NVARCHAR(100) '$.ciudad',
            FechaNacimientoTexto NVARCHAR(30) '$.fechaNacimiento',
            FechaRegistroTexto NVARCHAR(30) '$.fechaRegistro',
            EstadoTexto NVARCHAR(30) '$.estado'
        );

        INSERT INTO @Productos
        (
            IdProductoOrigen, CodigoProducto, NombreProducto,
            CategoriaTexto, Precio, EstadoTexto
        )
        SELECT
            IdProductoOrigen, CodigoProducto, NombreProducto,
            CategoriaTexto, Precio, EstadoTexto
        FROM OPENJSON(@DatosJson, '$.productos')
        WITH
        (
            IdProductoOrigen INT '$.idProductoOrigen',
            CodigoProducto NVARCHAR(30) '$.codigo',
            NombreProducto NVARCHAR(160) '$.nombre',
            CategoriaTexto NVARCHAR(100) '$.categoria',
            Precio DECIMAL(18,2) '$.precio',
            EstadoTexto NVARCHAR(30) '$.estado'
        );

        INSERT INTO @Facturas
        (
            IdFacturaOrigen, NumeroFactura, IdClienteOrigen,
            FechaEmisionTexto, EstadoTexto, Subtotal, IVA, Total
        )
        SELECT
            IdFacturaOrigen, NumeroFactura, IdClienteOrigen,
            FechaEmisionTexto, EstadoTexto, Subtotal, IVA, Total
        FROM OPENJSON(@DatosJson, '$.facturas')
        WITH
        (
            IdFacturaOrigen INT '$.idFacturaOrigen',
            NumeroFactura NVARCHAR(40) '$.numeroFactura',
            IdClienteOrigen INT '$.idClienteOrigen',
            FechaEmisionTexto NVARCHAR(30) '$.fechaEmision',
            EstadoTexto NVARCHAR(30) '$.estado',
            Subtotal DECIMAL(18,2) '$.subtotal',
            IVA DECIMAL(18,2) '$.iva',
            Total DECIMAL(18,2) '$.total'
        );

        INSERT INTO @Detalles
        (
            IdDetalleOrigen, IdFacturaOrigen, IdProductoOrigen,
            Cantidad, PrecioUnitario, Descuento, TotalLinea
        )
        SELECT
            IdDetalleOrigen, IdFacturaOrigen, IdProductoOrigen,
            Cantidad, PrecioUnitario, COALESCE(Descuento, 0), TotalLinea
        FROM OPENJSON(@DatosJson, '$.detalles')
        WITH
        (
            IdDetalleOrigen INT '$.idDetalleOrigen',
            IdFacturaOrigen INT '$.idFacturaOrigen',
            IdProductoOrigen INT '$.idProductoOrigen',
            Cantidad INT '$.cantidad',
            PrecioUnitario DECIMAL(18,2) '$.precioUnitario',
            Descuento DECIMAL(18,2) '$.descuento',
            TotalLinea DECIMAL(18,2) '$.totalLinea'
        );

        SELECT @ClientesLeidos = COUNT(*) FROM @Clientes;
        SELECT @ProductosLeidos = COUNT(*) FROM @Productos;
        SELECT @FacturasLeidas = COUNT(*) FROM @Facturas;
        SELECT @DetallesLeidos = COUNT(*) FROM @Detalles;

        IF @ClientesLeidos = 0
            THROW 51001, N'El JSON no contiene clientes.', 1;
        IF @ProductosLeidos = 0
            THROW 51002, N'El JSON no contiene productos.', 1;

        IF EXISTS
        (
            SELECT 1
            FROM @Facturas AS f
            LEFT JOIN @Clientes AS c ON c.IdClienteOrigen = f.IdClienteOrigen
            LEFT JOIN dbo.ClienteOrigen AS ce ON ce.IdClienteOrigen = f.IdClienteOrigen
            WHERE c.IdClienteOrigen IS NULL
              AND (@Reiniciar = 1 OR ce.IdClienteOrigen IS NULL)
        )
            THROW 51003, N'Existen facturas que apuntan a clientes inexistentes.', 1;

        IF EXISTS
        (
            SELECT 1
            FROM @Detalles AS d
            LEFT JOIN @Facturas AS f ON f.IdFacturaOrigen = d.IdFacturaOrigen
            LEFT JOIN dbo.FacturaOrigen AS fe ON fe.IdFacturaOrigen = d.IdFacturaOrigen
            WHERE f.IdFacturaOrigen IS NULL
              AND (@Reiniciar = 1 OR fe.IdFacturaOrigen IS NULL)
        )
            THROW 51004, N'Existen detalles que apuntan a facturas inexistentes.', 1;

        IF EXISTS
        (
            SELECT 1
            FROM @Detalles AS d
            LEFT JOIN @Productos AS p ON p.IdProductoOrigen = d.IdProductoOrigen
            LEFT JOIN dbo.ProductoOrigen AS pe ON pe.IdProductoOrigen = d.IdProductoOrigen
            WHERE p.IdProductoOrigen IS NULL
              AND (@Reiniciar = 1 OR pe.IdProductoOrigen IS NULL)
        )
            THROW 51005, N'Existen detalles que apuntan a productos inexistentes.', 1;

        BEGIN TRANSACTION;

        IF @Reiniciar = 1
        BEGIN
            DELETE FROM dbo.FacturaDetalleOrigen;
            DELETE FROM dbo.FacturaOrigen;
            DELETE FROM dbo.ProductoOrigen;
            DELETE FROM dbo.ClienteOrigen;
        END;

        MERGE dbo.ClienteOrigen AS destino
        USING @Clientes AS origen
            ON destino.IdClienteOrigen = origen.IdClienteOrigen
        WHEN MATCHED THEN
            UPDATE SET
                Documento = origen.Documento,
                Nombre = origen.Nombre,
                Apellido = origen.Apellido,
                Correo = origen.Correo,
                Telefono = origen.Telefono,
                Direccion = origen.Direccion,
                Ciudad = origen.Ciudad,
                FechaNacimientoTexto = origen.FechaNacimientoTexto,
                FechaRegistroTexto = origen.FechaRegistroTexto,
                EstadoTexto = origen.EstadoTexto,
                FechaActualizacion = SYSUTCDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
                Direccion, Ciudad, FechaNacimientoTexto, FechaRegistroTexto, EstadoTexto
            )
            VALUES
            (
                origen.IdClienteOrigen, origen.Documento, origen.Nombre, origen.Apellido,
                origen.Correo, origen.Telefono, origen.Direccion, origen.Ciudad,
                origen.FechaNacimientoTexto, origen.FechaRegistroTexto, origen.EstadoTexto
            );

        MERGE dbo.ProductoOrigen AS destino
        USING @Productos AS origen
            ON destino.IdProductoOrigen = origen.IdProductoOrigen
        WHEN MATCHED THEN
            UPDATE SET
                CodigoProducto = origen.CodigoProducto,
                NombreProducto = origen.NombreProducto,
                CategoriaTexto = origen.CategoriaTexto,
                Precio = origen.Precio,
                EstadoTexto = origen.EstadoTexto,
                FechaActualizacion = SYSUTCDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                IdProductoOrigen, CodigoProducto, NombreProducto,
                CategoriaTexto, Precio, EstadoTexto
            )
            VALUES
            (
                origen.IdProductoOrigen, origen.CodigoProducto, origen.NombreProducto,
                origen.CategoriaTexto, origen.Precio, origen.EstadoTexto
            );

        MERGE dbo.FacturaOrigen AS destino
        USING @Facturas AS origen
            ON destino.IdFacturaOrigen = origen.IdFacturaOrigen
        WHEN MATCHED THEN
            UPDATE SET
                NumeroFactura = origen.NumeroFactura,
                IdClienteOrigen = origen.IdClienteOrigen,
                FechaEmisionTexto = origen.FechaEmisionTexto,
                EstadoTexto = origen.EstadoTexto,
                Subtotal = origen.Subtotal,
                IVA = origen.IVA,
                Total = origen.Total,
                FechaActualizacion = SYSUTCDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                IdFacturaOrigen, NumeroFactura, IdClienteOrigen,
                FechaEmisionTexto, EstadoTexto, Subtotal, IVA, Total
            )
            VALUES
            (
                origen.IdFacturaOrigen, origen.NumeroFactura, origen.IdClienteOrigen,
                origen.FechaEmisionTexto, origen.EstadoTexto,
                origen.Subtotal, origen.IVA, origen.Total
            );

        MERGE dbo.FacturaDetalleOrigen AS destino
        USING @Detalles AS origen
            ON destino.IdDetalleOrigen = origen.IdDetalleOrigen
        WHEN MATCHED THEN
            UPDATE SET
                IdFacturaOrigen = origen.IdFacturaOrigen,
                IdProductoOrigen = origen.IdProductoOrigen,
                Cantidad = origen.Cantidad,
                PrecioUnitario = origen.PrecioUnitario,
                Descuento = origen.Descuento,
                TotalLinea = origen.TotalLinea,
                FechaActualizacion = SYSUTCDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                IdDetalleOrigen, IdFacturaOrigen, IdProductoOrigen,
                Cantidad, PrecioUnitario, Descuento, TotalLinea
            )
            VALUES
            (
                origen.IdDetalleOrigen, origen.IdFacturaOrigen, origen.IdProductoOrigen,
                origen.Cantidad, origen.PrecioUnitario, origen.Descuento, origen.TotalLinea
            );

        INSERT INTO dbo.CargaOrigenLog
        (
            FechaInicio, FechaFin, ArchivoOrigen, HashJson,
            ClientesLeidos, ProductosLeidos, FacturasLeidas, DetallesLeidos,
            Estado, Mensaje
        )
        VALUES
        (
            @FechaInicio, SYSUTCDATETIME(), @ArchivoOrigen,
            HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), @DatosJson)),
            @ClientesLeidos, @ProductosLeidos, @FacturasLeidas, @DetallesLeidos,
            N'EXITOSO', N'Los datos de origen fueron cargados o actualizados correctamente.'
        );

        COMMIT TRANSACTION;

        SELECT
            CAST(1 AS BIT) AS Exitoso,
            @ClientesLeidos AS ClientesProcesados,
            @ProductosLeidos AS ProductosProcesados,
            @FacturasLeidas AS FacturasProcesadas,
            @DetallesLeidos AS DetallesProcesados,
            N'Carga finalizada correctamente.' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0
            ROLLBACK TRANSACTION;

        INSERT INTO dbo.CargaOrigenError
        (
            Procedimiento, NumeroError, LineaError, MensajeError, FragmentoJson
        )
        VALUES
        (
            ERROR_PROCEDURE(), ERROR_NUMBER(), ERROR_LINE(), ERROR_MESSAGE(),
            LEFT(@DatosJson, 2000)
        );

        THROW;
    END CATCH;
END;
GO
