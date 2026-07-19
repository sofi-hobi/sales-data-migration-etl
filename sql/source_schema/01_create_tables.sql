:setvar DatabaseName "SmartCleanOrigen"
:setvar DataPath "/usr/src/app/data/datos_origen.json"

USE master;
GO

IF DB_ID(N'$(DatabaseName)') IS NULL
BEGIN
    PRINT N'Creando base de datos $(DatabaseName)...';
    CREATE DATABASE [$(DatabaseName)];
END;
GO

ALTER DATABASE [$(DatabaseName)] SET RECOVERY SIMPLE;
GO

USE [$(DatabaseName)];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- Se eliminan en orden inverso para permitir reconstruir el entorno.
DROP TABLE IF EXISTS dbo.FacturaDetalleOrigen;
DROP TABLE IF EXISTS dbo.FacturaOrigen;
DROP TABLE IF EXISTS dbo.ProductoOrigen;
DROP TABLE IF EXISTS dbo.ClienteOrigen;
DROP TABLE IF EXISTS dbo.CargaOrigenError;
DROP TABLE IF EXISTS dbo.CargaOrigenLog;
GO

CREATE TABLE dbo.ClienteOrigen
(
    IdClienteOrigen       INT            NOT NULL,
    Documento             NVARCHAR(30)   NULL,
    Nombre                NVARCHAR(100)  NULL,
    Apellido              NVARCHAR(120)  NULL,
    Correo                NVARCHAR(180)  NULL,
    Telefono              NVARCHAR(50)   NULL,
    Direccion             NVARCHAR(250)  NULL,
    Ciudad                NVARCHAR(100)  NULL,
    FechaNacimientoTexto  NVARCHAR(30)   NULL,
    FechaRegistroTexto    NVARCHAR(30)   NULL,
    EstadoTexto           NVARCHAR(30)   NULL,
    FechaCreacionSistema  DATETIME2(0)   NOT NULL CONSTRAINT DF_ClienteOrigen_FechaCreacion DEFAULT SYSUTCDATETIME(),
    FechaActualizacion    DATETIME2(0)   NULL,
    CONSTRAINT PK_ClienteOrigen PRIMARY KEY (IdClienteOrigen)
);
GO

CREATE TABLE dbo.ProductoOrigen
(
    IdProductoOrigen      INT            NOT NULL,
    CodigoProducto        NVARCHAR(30)   NULL,
    NombreProducto        NVARCHAR(160)  NULL,
    CategoriaTexto        NVARCHAR(100)  NULL,
    Precio                DECIMAL(18,2)  NULL,
    EstadoTexto           NVARCHAR(30)   NULL,
    FechaCreacionSistema  DATETIME2(0)   NOT NULL CONSTRAINT DF_ProductoOrigen_FechaCreacion DEFAULT SYSUTCDATETIME(),
    FechaActualizacion    DATETIME2(0)   NULL,
    CONSTRAINT PK_ProductoOrigen PRIMARY KEY (IdProductoOrigen),
    CONSTRAINT CK_ProductoOrigen_Precio CHECK (Precio IS NULL OR Precio >= 0)
);
GO

CREATE TABLE dbo.FacturaOrigen
(
    IdFacturaOrigen       INT            NOT NULL,
    NumeroFactura         NVARCHAR(40)   NOT NULL,
    IdClienteOrigen       INT            NOT NULL,
    FechaEmisionTexto     NVARCHAR(30)   NULL,
    EstadoTexto           NVARCHAR(30)   NULL,
    Subtotal              DECIMAL(18,2)  NOT NULL,
    IVA                   DECIMAL(18,2)  NOT NULL,
    Total                 DECIMAL(18,2)  NOT NULL,
    FechaCreacionSistema  DATETIME2(0)   NOT NULL CONSTRAINT DF_FacturaOrigen_FechaCreacion DEFAULT SYSUTCDATETIME(),
    FechaActualizacion    DATETIME2(0)   NULL,
    CONSTRAINT PK_FacturaOrigen PRIMARY KEY (IdFacturaOrigen),
    CONSTRAINT FK_FacturaOrigen_ClienteOrigen
        FOREIGN KEY (IdClienteOrigen) REFERENCES dbo.ClienteOrigen(IdClienteOrigen),
    CONSTRAINT CK_FacturaOrigen_Montos CHECK (Subtotal >= 0 AND IVA >= 0 AND Total >= 0)
);
GO

CREATE TABLE dbo.FacturaDetalleOrigen
(
    IdDetalleOrigen       INT            NOT NULL,
    IdFacturaOrigen       INT            NOT NULL,
    IdProductoOrigen      INT            NOT NULL,
    Cantidad              INT            NOT NULL,
    PrecioUnitario        DECIMAL(18,2)  NOT NULL,
    Descuento             DECIMAL(18,2)  NOT NULL CONSTRAINT DF_FacturaDetalleOrigen_Descuento DEFAULT (0),
    TotalLinea            DECIMAL(18,2)  NOT NULL,
    FechaCreacionSistema  DATETIME2(0)   NOT NULL CONSTRAINT DF_FacturaDetalleOrigen_FechaCreacion DEFAULT SYSUTCDATETIME(),
    FechaActualizacion    DATETIME2(0)   NULL,
    CONSTRAINT PK_FacturaDetalleOrigen PRIMARY KEY (IdDetalleOrigen),
    CONSTRAINT FK_FacturaDetalleOrigen_FacturaOrigen
        FOREIGN KEY (IdFacturaOrigen) REFERENCES dbo.FacturaOrigen(IdFacturaOrigen),
    CONSTRAINT FK_FacturaDetalleOrigen_ProductoOrigen
        FOREIGN KEY (IdProductoOrigen) REFERENCES dbo.ProductoOrigen(IdProductoOrigen),
    CONSTRAINT CK_FacturaDetalleOrigen_Valores
        CHECK (Cantidad > 0 AND PrecioUnitario >= 0 AND Descuento >= 0 AND TotalLinea >= 0)
);
GO

CREATE TABLE dbo.CargaOrigenLog
(
    IdCarga               BIGINT         IDENTITY(1,1) NOT NULL,
    FechaInicio           DATETIME2(0)   NOT NULL,
    FechaFin              DATETIME2(0)   NULL,
    ArchivoOrigen         NVARCHAR(260)  NULL,
    HashJson              VARBINARY(32)  NULL,
    ClientesLeidos        INT            NOT NULL CONSTRAINT DF_CargaOrigenLog_Clientes DEFAULT (0),
    ProductosLeidos       INT            NOT NULL CONSTRAINT DF_CargaOrigenLog_Productos DEFAULT (0),
    FacturasLeidas        INT            NOT NULL CONSTRAINT DF_CargaOrigenLog_Facturas DEFAULT (0),
    DetallesLeidos        INT            NOT NULL CONSTRAINT DF_CargaOrigenLog_Detalles DEFAULT (0),
    Estado                NVARCHAR(20)   NOT NULL,
    Mensaje               NVARCHAR(2000) NULL,
    CONSTRAINT PK_CargaOrigenLog PRIMARY KEY (IdCarga)
);
GO

CREATE TABLE dbo.CargaOrigenError
(
    IdError               BIGINT         IDENTITY(1,1) NOT NULL,
    FechaError            DATETIME2(0)   NOT NULL CONSTRAINT DF_CargaOrigenError_Fecha DEFAULT SYSUTCDATETIME(),
    Procedimiento         SYSNAME        NULL,
    NumeroError           INT            NULL,
    LineaError            INT            NULL,
    MensajeError          NVARCHAR(4000) NOT NULL,
    FragmentoJson         NVARCHAR(2000) NULL,
    CONSTRAINT PK_CargaOrigenError PRIMARY KEY (IdError)
);
GO

-- Índices de consulta. No se usan restricciones UNIQUE porque el origen
-- debe conservar documentos, correos y teléfonos duplicados.
CREATE INDEX IX_ClienteOrigen_Documento ON dbo.ClienteOrigen (Documento);
CREATE INDEX IX_ClienteOrigen_Correo ON dbo.ClienteOrigen (Correo);
CREATE INDEX IX_ClienteOrigen_Telefono ON dbo.ClienteOrigen (Telefono);
CREATE INDEX IX_ProductoOrigen_Codigo ON dbo.ProductoOrigen (CodigoProducto);
CREATE INDEX IX_FacturaOrigen_Cliente ON dbo.FacturaOrigen (IdClienteOrigen);
CREATE INDEX IX_FacturaOrigen_Numero ON dbo.FacturaOrigen (NumeroFactura);
CREATE INDEX IX_FacturaDetalleOrigen_Factura ON dbo.FacturaDetalleOrigen (IdFacturaOrigen);
CREATE INDEX IX_FacturaDetalleOrigen_Producto ON dbo.FacturaDetalleOrigen (IdProductoOrigen);
GO
