-- El Integrante 1 debe llenar este archivo con las instrucciones para crear la BD, tablas y datos con errores

USE master;
GO

IF DB_ID('ETL_Origen') IS NOT NULL
BEGIN
    ALTER DATABASE ETL_Origen SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ETL_Origen;
END
GO

CREATE DATABASE ETL_Origen;
GO

USE ETL_Origen;
GO

DROP TABLE IF EXISTS ConsolidacionCliente;
DROP TABLE IF EXISTS FacturaDetalleOrigen;
DROP TABLE IF EXISTS FacturaOrigen;
DROP TABLE IF EXISTS ProductoOrigen;
DROP TABLE IF EXISTS ClienteOrigen;
GO


CREATE TABLE ClienteOrigen (
    IdClienteOrigen     INT IDENTITY(1,1)
                        CONSTRAINT PK_ClienteOrigen_IdClienteOrigen PRIMARY KEY CLUSTERED,
    Nombre              NVARCHAR(50) NOT NULL,
    Apellido            NVARCHAR(50) NOT NULL,
    Cedula              NVARCHAR(10) NOT NULL
                        CONSTRAINT UQ_ClienteOrigen_Cedula UNIQUE,
    Correo              NVARCHAR(100),
    Telefono            VARCHAR(15),
    Direccion           NVARCHAR(150),
    -- Auditoría
    Estado              VARCHAR(1) NOT NULL
                        CONSTRAINT DF_ClienteOrigen_Estado DEFAULT ('A')
                        CONSTRAINT CK_ClienteOrigen_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion       DATETIME NOT NULL
                        CONSTRAINT DF_ClienteOrigen_FechaCreacion DEFAULT GETDATE(),
    FechaModifica       DATETIME NULL,
    IdUsuarioCreacion   INT NULL,
    IdUsuarioModifica   INT NULL
);
GO


CREATE TABLE ProductoOrigen (
    IdProductoOrigen    INT IDENTITY(1,1)
                        CONSTRAINT PK_ProductoOrigen_IdProductoOrigen PRIMARY KEY CLUSTERED,
    Nombre              NVARCHAR(100) NOT NULL,
    Categoria           NVARCHAR(50),
    Precio              DECIMAL(10,2) NOT NULL
                        CONSTRAINT CK_ProductoOrigen_Precio CHECK (Precio >= 0),
    Stock               INT NOT NULL
                        CONSTRAINT CK_ProductoOrigen_Stock CHECK (Stock >= 0),
    -- Auditoría
    Estado              VARCHAR(1) NOT NULL
                        CONSTRAINT DF_ProductoOrigen_Estado DEFAULT ('A')
                        CONSTRAINT CK_ProductoOrigen_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion       DATETIME NOT NULL
                        CONSTRAINT DF_ProductoOrigen_FechaCreacion DEFAULT GETDATE(),
    FechaModifica       DATETIME NULL,
    IdUsuarioCreacion   INT NULL,
    IdUsuarioModifica   INT NULL
);
GO


CREATE TABLE FacturaOrigen (
    IdFacturaOrigen     INT IDENTITY(1,1)
                        CONSTRAINT PK_FacturaOrigen_IdFacturaOrigen PRIMARY KEY CLUSTERED,
    IdClienteOrigen     INT NOT NULL,
    NumeroFactura       NVARCHAR(20) NOT NULL
                        CONSTRAINT UQ_FacturaOrigen_NumeroFactura UNIQUE,
    FechaFactura        DATE NOT NULL,
    Subtotal            DECIMAL(10,2) NOT NULL
                        CONSTRAINT CK_FacturaOrigen_Subtotal CHECK (Subtotal >= 0),
    IVA                 DECIMAL(10,2) NOT NULL
                        CONSTRAINT CK_FacturaOrigen_IVA CHECK (IVA >= 0),
    Total               DECIMAL(10,2) NOT NULL
                        CONSTRAINT CK_FacturaOrigen_Total CHECK (Total >= 0),
    -- Auditoría
    Estado              VARCHAR(1) NOT NULL
                        CONSTRAINT DF_FacturaOrigen_Estado DEFAULT ('A')
                        CONSTRAINT CK_FacturaOrigen_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion       DATETIME NOT NULL
                        CONSTRAINT DF_FacturaOrigen_FechaCreacion DEFAULT GETDATE(),
    FechaModifica       DATETIME NULL,
    IdUsuarioCreacion   INT NULL,
    IdUsuarioModifica   INT NULL,
    -- Relaciones
    CONSTRAINT FK_FacturaOrigen_ClienteOrigen FOREIGN KEY (IdClienteOrigen) REFERENCES ClienteOrigen(IdClienteOrigen)
);
GO


CREATE TABLE FacturaDetalleOrigen (
    IdFacturaDetalleOrigen INT IDENTITY(1,1)
                           CONSTRAINT PK_FacturaDetalleOrigen_IdFacturaDetalleOrigen PRIMARY KEY CLUSTERED,
    IdFacturaOrigen        INT NOT NULL,
    IdProductoOrigen       INT NOT NULL,
    Cantidad               INT NOT NULL
                           CONSTRAINT CK_FacturaDetalleOrigen_Cantidad CHECK (Cantidad > 0),
    PrecioUnitario         DECIMAL(10,2) NOT NULL
                           CONSTRAINT CK_FacturaDetalleOrigen_Precio CHECK (PrecioUnitario >= 0),
    Subtotal               DECIMAL(10,2) NOT NULL
                           CONSTRAINT CK_FacturaDetalleOrigen_Subtotal CHECK (Subtotal >= 0),
    -- Auditoría
    Estado                 VARCHAR(1) NOT NULL
                           CONSTRAINT DF_FacturaDetalleOrigen_Estado DEFAULT ('A')
                           CONSTRAINT CK_FacturaDetalleOrigen_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion          DATETIME NOT NULL
                           CONSTRAINT DF_FacturaDetalleOrigen_FechaCreacion DEFAULT GETDATE(),
    FechaModifica          DATETIME NULL,
    IdUsuarioCreacion      INT NULL,
    IdUsuarioModifica      INT NULL,
    -- Relaciones
    CONSTRAINT FK_FacturaDetalleOrigen_FacturaOrigen FOREIGN KEY (IdFacturaOrigen) REFERENCES FacturaOrigen(IdFacturaOrigen),
    CONSTRAINT FK_FacturaDetalleOrigen_ProductoOrigen FOREIGN KEY (IdProductoOrigen) REFERENCES ProductoOrigen(IdProductoOrigen)
);
GO


CREATE TABLE ConsolidacionCliente (
    IdConsolidacionCliente INT IDENTITY(1,1)
                           CONSTRAINT PK_ConsolidacionCliente_IdConsolidacionCliente PRIMARY KEY CLUSTERED,
    IdClientePrincipal     INT NOT NULL,
    IdClienteDuplicado     INT NOT NULL,
    IdFacturaOrigen        INT NULL,
    Accion                 NVARCHAR(50) NOT NULL,
    Motivo                 NVARCHAR(200),
    Descripcion             NVARCHAR(300),
    FechaConsolidacion     DATETIME NOT NULL
                           CONSTRAINT DF_ConsolidacionCliente_FechaConsolidacion DEFAULT GETDATE(),
    -- Auditoría
    Estado                 VARCHAR(1) NOT NULL
                           CONSTRAINT DF_ConsolidacionCliente_Estado DEFAULT ('A')
                           CONSTRAINT CK_ConsolidacionCliente_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion          DATETIME NOT NULL
                           CONSTRAINT DF_ConsolidacionCliente_FechaCreacion DEFAULT GETDATE(),
    FechaModifica          DATETIME NULL,
    IdUsuarioCreacion      INT NULL,
    IdUsuarioModifica      INT NULL,
    -- Relaciones
    CONSTRAINT FK_ConsolidacionCliente_Principal FOREIGN KEY (IdClientePrincipal) REFERENCES ClienteOrigen(IdClienteOrigen),
    CONSTRAINT FK_ConsolidacionCliente_Duplicado FOREIGN KEY (IdClienteDuplicado) REFERENCES ClienteOrigen(IdClienteOrigen),
    CONSTRAINT FK_ConsolidacionCliente_FacturaOrigen FOREIGN KEY (IdFacturaOrigen) REFERENCES FacturaOrigen(IdFacturaOrigen)
);
GO