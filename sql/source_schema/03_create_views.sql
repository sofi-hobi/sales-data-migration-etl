USE SmartCleanOrigen;
GO

CREATE OR ALTER VIEW dbo.vw_ResumenBaseOrigen
AS
SELECT
    (SELECT COUNT(*) FROM dbo.ClienteOrigen) AS CantidadClientes,
    (SELECT COUNT(*) FROM dbo.ProductoOrigen) AS CantidadProductos,
    (SELECT COUNT(*) FROM dbo.FacturaOrigen) AS CantidadFacturas,
    (SELECT COUNT(*) FROM dbo.FacturaDetalleOrigen) AS CantidadDetalles,
    (SELECT COALESCE(SUM(Total), 0) FROM dbo.FacturaOrigen) AS TotalFacturado,
    (SELECT COUNT(*) FROM dbo.CargaOrigenError) AS ErroresDeCarga;
GO

CREATE OR ALTER VIEW dbo.vw_TotalVentasOrigen
AS
SELECT
    COUNT(*) AS CantidadFacturas,
    COALESCE(SUM(Subtotal), 0) AS SubtotalFacturado,
    COALESCE(SUM(IVA), 0) AS IVAFacturado,
    COALESCE(SUM(Total), 0) AS TotalFacturado
FROM dbo.FacturaOrigen;
GO

CREATE OR ALTER VIEW dbo.vw_FacturasConCliente
AS
SELECT
    f.IdFacturaOrigen,
    f.NumeroFactura,
    f.FechaEmisionTexto,
    f.EstadoTexto AS EstadoFactura,
    f.Subtotal,
    f.IVA,
    f.Total,
    c.IdClienteOrigen,
    c.Documento,
    CONCAT(c.Nombre, N' ', c.Apellido) AS Cliente,
    c.Correo,
    c.Telefono
FROM dbo.FacturaOrigen AS f
INNER JOIN dbo.ClienteOrigen AS c
    ON c.IdClienteOrigen = f.IdClienteOrigen;
GO

CREATE OR ALTER VIEW dbo.vw_DatosInconsistentesCliente
AS
SELECT
    c.*,
    CAST(CASE
        WHEN c.Correo IS NULL
          OR LTRIM(RTRIM(c.Correo)) = N''
          OR c.Correo LIKE N'% %'
          OR c.Correo NOT LIKE N'%_@_%._%'
        THEN 1 ELSE 0 END AS BIT) AS CorreoInvalido,
    CAST(CASE
        WHEN c.Telefono IS NULL
          OR LEN(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(c.Telefono, N' ', N''), N'-', N''), N'(', N''), N')', N''), N'+', N'')) < 10
          OR REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(c.Telefono, N' ', N''), N'-', N''), N'(', N''), N')', N''), N'+', N'') LIKE N'%[^0-9]%'
        THEN 1 ELSE 0 END AS BIT) AS TelefonoInvalido,
    CAST(CASE
        WHEN c.Documento IS NULL
          OR LEN(REPLACE(REPLACE(LTRIM(RTRIM(c.Documento)), N'-', N''), N' ', N'')) <> 10
        THEN 1 ELSE 0 END AS BIT) AS DocumentoInvalido,
    CAST(CASE
        WHEN c.FechaNacimientoTexto IS NULL
          OR COALESCE(
                TRY_CONVERT(DATE, c.FechaNacimientoTexto, 23),
                TRY_CONVERT(DATE, c.FechaNacimientoTexto, 103),
                TRY_CONVERT(DATE, c.FechaNacimientoTexto, 111)
             ) IS NULL
        THEN 1 ELSE 0 END AS BIT) AS FechaNacimientoInvalida,
    CAST(CASE
        WHEN c.FechaRegistroTexto IS NULL
          OR COALESCE(
                TRY_CONVERT(DATE, c.FechaRegistroTexto, 23),
                TRY_CONVERT(DATE, c.FechaRegistroTexto, 103),
                TRY_CONVERT(DATE, c.FechaRegistroTexto, 111)
             ) IS NULL
        THEN 1 ELSE 0 END AS BIT) AS FechaRegistroInvalida
FROM dbo.ClienteOrigen AS c;
GO

CREATE OR ALTER VIEW dbo.vw_ClientesPotencialmenteDuplicados
AS
WITH Normalizados AS
(
    SELECT
        c.*,
        NULLIF(REPLACE(REPLACE(REPLACE(LOWER(LTRIM(RTRIM(c.Documento))), N' ', N''), N'-', N''), N'.', N''), N'') AS DocumentoNormalizado,
        NULLIF(REPLACE(LOWER(LTRIM(RTRIM(c.Correo))), N' ', N''), N'') AS CorreoNormalizado,
        NULLIF(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                LOWER(LTRIM(RTRIM(c.Telefono))),
                N' ', N''), N'-', N''), N'(', N''), N')', N''), N'+', N''), N'.', N''),
            N''
        ) AS TelefonoNormalizado,
        LOWER(LTRIM(RTRIM(CONCAT(c.Nombre, N' ', c.Apellido)))) AS NombreNormalizado
    FROM dbo.ClienteOrigen AS c
)
SELECT
    a.IdClienteOrigen AS IdClienteA,
    b.IdClienteOrigen AS IdClienteB,
    CONCAT(a.Nombre, N' ', a.Apellido) AS ClienteA,
    CONCAT(b.Nombre, N' ', b.Apellido) AS ClienteB,
    CAST(CASE WHEN a.DocumentoNormalizado IS NOT NULL
                   AND a.DocumentoNormalizado = b.DocumentoNormalizado THEN 1 ELSE 0 END AS BIT) AS CoincideDocumento,
    CAST(CASE WHEN a.CorreoNormalizado IS NOT NULL
                   AND a.CorreoNormalizado = b.CorreoNormalizado THEN 1 ELSE 0 END AS BIT) AS CoincideCorreo,
    CAST(CASE WHEN a.TelefonoNormalizado IS NOT NULL
                   AND a.TelefonoNormalizado = b.TelefonoNormalizado THEN 1 ELSE 0 END AS BIT) AS CoincideTelefono,
    DIFFERENCE(a.NombreNormalizado, b.NombreNormalizado) AS SimilitudSoundex,
    (
        CASE WHEN a.DocumentoNormalizado IS NOT NULL
                  AND a.DocumentoNormalizado = b.DocumentoNormalizado THEN 100 ELSE 0 END
      + CASE WHEN a.CorreoNormalizado IS NOT NULL
                  AND a.CorreoNormalizado = b.CorreoNormalizado THEN 50 ELSE 0 END
      + CASE WHEN a.TelefonoNormalizado IS NOT NULL
                  AND a.TelefonoNormalizado = b.TelefonoNormalizado THEN 40 ELSE 0 END
      + CASE WHEN DIFFERENCE(a.NombreNormalizado, b.NombreNormalizado) >= 3 THEN 20 ELSE 0 END
    ) AS PuntajeSugerido,
    CASE
        WHEN a.DocumentoNormalizado IS NOT NULL
         AND a.DocumentoNormalizado = b.DocumentoNormalizado THEN N'DUPLICADO EXACTO'
        WHEN (
            CASE WHEN a.CorreoNormalizado IS NOT NULL
                      AND a.CorreoNormalizado = b.CorreoNormalizado THEN 50 ELSE 0 END
          + CASE WHEN a.TelefonoNormalizado IS NOT NULL
                      AND a.TelefonoNormalizado = b.TelefonoNormalizado THEN 40 ELSE 0 END
          + CASE WHEN DIFFERENCE(a.NombreNormalizado, b.NombreNormalizado) >= 3 THEN 20 ELSE 0 END
        ) >= 70 THEN N'DUPLICADO PROBABLE'
        ELSE N'REVISIÓN MANUAL'
    END AS Clasificacion
FROM Normalizados AS a
INNER JOIN Normalizados AS b
    ON a.IdClienteOrigen < b.IdClienteOrigen
WHERE
       (a.DocumentoNormalizado IS NOT NULL AND a.DocumentoNormalizado = b.DocumentoNormalizado)
    OR (a.CorreoNormalizado IS NOT NULL AND a.CorreoNormalizado = b.CorreoNormalizado)
    OR (a.TelefonoNormalizado IS NOT NULL AND a.TelefonoNormalizado = b.TelefonoNormalizado)
    OR DIFFERENCE(a.NombreNormalizado, b.NombreNormalizado) >= 3;
GO

CREATE OR ALTER VIEW dbo.vw_IntegridadOrigen
AS
SELECT
    (SELECT COUNT(*)
     FROM dbo.FacturaOrigen AS f
     LEFT JOIN dbo.ClienteOrigen AS c ON c.IdClienteOrigen = f.IdClienteOrigen
     WHERE c.IdClienteOrigen IS NULL) AS FacturasSinCliente,
    (SELECT COUNT(*)
     FROM dbo.FacturaDetalleOrigen AS d
     LEFT JOIN dbo.FacturaOrigen AS f ON f.IdFacturaOrigen = d.IdFacturaOrigen
     WHERE f.IdFacturaOrigen IS NULL) AS DetallesSinFactura,
    (SELECT COUNT(*)
     FROM dbo.FacturaDetalleOrigen AS d
     LEFT JOIN dbo.ProductoOrigen AS p ON p.IdProductoOrigen = d.IdProductoOrigen
     WHERE p.IdProductoOrigen IS NULL) AS DetallesSinProducto;
GO
