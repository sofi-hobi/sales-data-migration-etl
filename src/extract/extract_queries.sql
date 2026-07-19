-- extract_queries.sql
-- extract_queries.sql
-- Consultas de extraccion contra SmartCleanOrigen (SQL Server).
-- Se ejecutan tal cual desde src/extract/sqlserver_connector.py::QUERIES.

SELECT
    IdClienteOrigen, Documento, Nombre, Apellido, Correo, Telefono,
    Direccion, Ciudad, FechaNacimientoTexto, FechaRegistroTexto,
    EstadoTexto, FechaCreacionSistema, FechaActualizacion
FROM dbo.ClienteOrigen;

SELECT
    IdProductoOrigen, CodigoProducto, NombreProducto, CategoriaTexto,
    Precio, EstadoTexto, FechaCreacionSistema, FechaActualizacion
FROM dbo.ProductoOrigen;

SELECT
    IdFacturaOrigen, NumeroFactura, IdClienteOrigen, FechaEmisionTexto,
    EstadoTexto, Subtotal, IVA, Total, FechaCreacionSistema, FechaActualizacion
FROM dbo.FacturaOrigen;

SELECT
    IdDetalleOrigen, IdFacturaOrigen, IdProductoOrigen, Cantidad,
    PrecioUnitario, Descuento, TotalLinea, FechaCreacionSistema, FechaActualizacion
FROM dbo.FacturaDetalleOrigen;
