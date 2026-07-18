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

DROP TABLE IF EXISTS SistemaBitacora;
DROP TABLE IF EXISTS CultivoProduccion;
DROP TABLE IF EXISTS CultivoCicloVida;
DROP TABLE IF EXISTS CultivoMetrica;
DROP TABLE IF EXISTS CultivoReglamento;
DROP TABLE IF EXISTS CultivoLote;
DROP TABLE IF EXISTS GranjaDispositivo;
DROP TABLE IF EXISTS CultivoInsumo;
DROP TABLE IF EXISTS CultivoAgronomo;
DROP TABLE IF EXISTS CultivoEtapa;
DROP TABLE IF EXISTS GranjaInstalacion;
GO


CREATE TABLE GranjaInstalacion (
    IdInstalacion        INT IDENTITY(1,1)
                         CONSTRAINT PK_GranjaInstalacion_IdInstalacion PRIMARY KEY CLUSTERED,
    IdInstalacionPadre   INT NULL,
    TipoNivel            NVARCHAR(50) NOT NULL,
    Nombre               NVARCHAR(100) NOT NULL,
    EstadoOperativo      NVARCHAR(30) NOT NULL,
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_GranjaInstalacion_Estado DEFAULT ('A')
                         CONSTRAINT CK_GranjaInstalacion_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_GranjaInstalacion_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_GranjaInstalacion_Padre FOREIGN KEY (IdInstalacionPadre) REFERENCES GranjaInstalacion(IdInstalacion)
);
GO


CREATE TABLE GranjaDispositivo (
    IdDispositivo        INT IDENTITY(1,1)
                         CONSTRAINT PK_GranjaDispositivo_IdDispositivo PRIMARY KEY CLUSTERED,
    IdInstalacion        INT NOT NULL,
    TipoDispositivo      NVARCHAR(50) NOT NULL,
    MacAddress           VARCHAR(50) NOT NULL
                         CONSTRAINT UQ_GranjaDispositivo_MacAddress UNIQUE,
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_GranjaDispositivo_Estado DEFAULT ('A')
                         CONSTRAINT CK_GranjaDispositivo_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_GranjaDispositivo_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_GranjaDispositivo_GranjaInstalacion FOREIGN KEY (IdInstalacion) REFERENCES GranjaInstalacion(IdInstalacion)
);
GO

CREATE TABLE CultivoAgronomo (
    IdAgronomo           INT IDENTITY(1,1)
                         CONSTRAINT PK_CultivoAgronomo_IdAgronomo PRIMARY KEY CLUSTERED,
    Nombre               NVARCHAR(100) NOT NULL,
    Especialidad         NVARCHAR(100) NOT NULL,
    Correo               NVARCHAR(100) NOT NULL
                         CONSTRAINT UQ_CultivoAgronomo_Correo UNIQUE,
    EstadoActividad      NVARCHAR(30) NOT NULL,
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_CultivoAgronomo_Estado DEFAULT ('A')
                         CONSTRAINT CK_CultivoAgronomo_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_CultivoAgronomo_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL
);
GO

CREATE TABLE CultivoInsumo (
    IdInsumo             INT IDENTITY(1,1)
                         CONSTRAINT PK_CultivoInsumo_IdInsumo PRIMARY KEY CLUSTERED,
    Nombre               NVARCHAR(100) NOT NULL
                         CONSTRAINT UQ_CultivoInsumo_Nombre UNIQUE,
    Tipo                 NVARCHAR(50) NOT NULL,
    Descripcion          NVARCHAR(250) NULL,
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_CultivoInsumo_Estado DEFAULT ('A')
                         CONSTRAINT CK_CultivoInsumo_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_CultivoInsumo_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL
);
GO

CREATE TABLE CultivoEtapa (
    IdEtapa               INT IDENTITY(1,1)
                          CONSTRAINT PK_CultivoEtapa_IdEtapa PRIMARY KEY CLUSTERED,
    Nombre                NVARCHAR(100) NOT NULL
                          CONSTRAINT UQ_CultivoEtapa_Nombre UNIQUE,
    EsEtapaFinal          BIT NOT NULL,
    Descripcion           NVARCHAR(250) NULL,
    -- Auditoría
    Estado                VARCHAR(1) NOT NULL
                          CONSTRAINT DF_CultivoEtapa_Estado DEFAULT ('A')
                          CONSTRAINT CK_CultivoEtapa_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion         DATETIME NOT NULL
                          CONSTRAINT DF_CultivoEtapa_FechaCreacion DEFAULT GETDATE(),
    FechaModifica         DATETIME NULL,
    IdUsuarioCreacion     INT NULL,
    IdUsuarioModifica     INT NULL
);
GO

CREATE TABLE CultivoReglamento (
    IdRegla               INT IDENTITY(1,1)
                          CONSTRAINT PK_CultivoReglamento_IdRegla PRIMARY KEY CLUSTERED,
    IdEtapaOrigen         INT NOT NULL,
    IdInsumo              INT NOT NULL,
    IdEtapaDestino        INT NOT NULL,
    JustificacionAgronomica NVARCHAR(300) NOT NULL,
    -- Auditoría
    Estado                VARCHAR(1) NOT NULL
                          CONSTRAINT DF_CultivoReglamento_Estado DEFAULT ('A')
                          CONSTRAINT CK_CultivoReglamento_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion         DATETIME NOT NULL
                          CONSTRAINT DF_CultivoReglamento_FechaCreacion DEFAULT GETDATE(),
    FechaModifica         DATETIME NULL,
    IdUsuarioCreacion     INT NULL,
    IdUsuarioModifica     INT NULL,
    -- Relaciones
    CONSTRAINT FK_CultivoReglamento_EtapaOrigen     FOREIGN KEY (IdEtapaOrigen)     REFERENCES CultivoEtapa(IdEtapa),
    CONSTRAINT FK_CultivoReglamento_Insumo          FOREIGN KEY (IdInsumo)          REFERENCES CultivoInsumo(IdInsumo),
    CONSTRAINT FK_CultivoReglamento_EtapaDestino    FOREIGN KEY (IdEtapaDestino)    REFERENCES CultivoEtapa(IdEtapa)
);
GO

CREATE TABLE CultivoLote (
    IdLote                INT IDENTITY(1,1)
                          CONSTRAINT PK_CultivoLote_IdLote PRIMARY KEY CLUSTERED,
    IdInstalacion         INT NOT NULL,
    IdAgronomo            INT NOT NULL,
    CepaGenetica          NVARCHAR(100) NOT NULL,
    FechaSiembra          DATETIME NOT NULL,
    -- Auditoría
    Estado                VARCHAR(1) NOT NULL
                          CONSTRAINT DF_CultivoLote_Estado DEFAULT ('A')
                          CONSTRAINT CK_CultivoLote_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion         DATETIME NOT NULL
                          CONSTRAINT DF_CultivoLote_FechaCreacion DEFAULT GETDATE(),
    FechaModifica         DATETIME NULL,
    IdUsuarioCreacion     INT NULL,
    IdUsuarioModifica     INT NULL,
    -- Relaciones
    CONSTRAINT FK_CultivoLote_GranjaInstalacion FOREIGN KEY (IdInstalacion) REFERENCES GranjaInstalacion(IdInstalacion),
    CONSTRAINT FK_CultivoLote_CultivoAgronomo   FOREIGN KEY (IdAgronomo)    REFERENCES CultivoAgronomo(IdAgronomo)
);
GO

CREATE TABLE CultivoMetrica (
    IdLectura             BIGINT IDENTITY(1,1)
                          CONSTRAINT PK_CultivoMetrica_IdLectura PRIMARY KEY CLUSTERED,
    IdDispositivo         INT NOT NULL,
    IdLote               INT NOT NULL,
    NivelLuzLux          DECIMAL(10,2) NOT NULL,
    PhAgua               DECIMAL(5,2) NOT NULL,
    NutrientesPPM        DECIMAL(10,2) NOT NULL,
    FechaHora            DATETIME NOT NULL
                         CONSTRAINT DF_CultivoMetrica_FechaHora DEFAULT GETDATE(),
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_CultivoMetrica_Estado DEFAULT ('A')
                         CONSTRAINT CK_CultivoMetrica_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_CultivoMetrica_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_CultivoMetrica_Dispositivo    FOREIGN KEY (IdDispositivo) REFERENCES GranjaDispositivo(IdDispositivo),
    CONSTRAINT FK_CultivoMetrica_Lote           FOREIGN KEY (IdLote)        REFERENCES CultivoLote(IdLote)
);
GO

CREATE TABLE CultivoCicloVida (
    IdRegistro           BIGINT IDENTITY(1,1)
                         CONSTRAINT PK_CultivoCicloVida_IdRegistro PRIMARY KEY CLUSTERED,
    IdLote               INT NOT NULL,
    IdEtapa              INT NOT NULL,
    IdInsumo             INT NULL,
    IdAgronomo           INT NOT NULL,
    Detonante            NVARCHAR(200) NOT NULL,
    FechaHora            DATETIME NOT NULL
                         CONSTRAINT DF_CultivoCicloVida_FechaHora DEFAULT GETDATE(),
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_CultivoCicloVida_Estado DEFAULT ('A')
                         CONSTRAINT CK_CultivoCicloVida_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_CultivoCicloVida_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_CultivoCicloVida_Lote     FOREIGN KEY (IdLote)        REFERENCES CultivoLote(IdLote),
    CONSTRAINT FK_CultivoCicloVida_Etapa    FOREIGN KEY (IdEtapa)       REFERENCES CultivoEtapa(IdEtapa),
    CONSTRAINT FK_CultivoCicloVida_Insumo   FOREIGN KEY (IdInsumo)      REFERENCES CultivoInsumo(IdInsumo),
    CONSTRAINT FK_CultivoCicloVida_Agronomo FOREIGN KEY (IdAgronomo)    REFERENCES CultivoAgronomo(IdAgronomo)
);
GO

CREATE TABLE CultivoProduccion (
    IdProduccion         BIGINT IDENTITY(1,1)
                         CONSTRAINT PK_CultivoProduccion_IdProduccion PRIMARY KEY CLUSTERED,
    IdLote               INT NOT NULL,
    IdRegla              INT NOT NULL,
    IdInsumo             INT NOT NULL,
    IdAgronomo           INT NOT NULL,
    FechaCosecha         DATETIME NOT NULL,
    PesoGramos           DECIMAL(10,2) NOT NULL,
    CalidadProducto      NVARCHAR(50) NOT NULL,
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_CultivoProduccion_Estado DEFAULT ('A')
                         CONSTRAINT CK_CultivoProduccion_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_CultivoProduccion_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_CultivoProduccion_Lote        FOREIGN KEY (IdLote)        REFERENCES CultivoLote(IdLote),
    CONSTRAINT FK_CultivoProduccion_Regla       FOREIGN KEY (IdRegla)       REFERENCES CultivoReglamento(IdRegla),
    CONSTRAINT FK_CultivoProduccion_Insumo      FOREIGN KEY (IdInsumo)      REFERENCES CultivoInsumo(IdInsumo),
    CONSTRAINT FK_CultivoProduccion_Agronomo    FOREIGN KEY (IdAgronomo)    REFERENCES CultivoAgronomo(IdAgronomo)
);
GO

CREATE TABLE SistemaBitacora (
    IdLog                BIGINT IDENTITY(1,1)
                         CONSTRAINT PK_SistemaBitacora_IdLog PRIMARY KEY CLUSTERED,
    TipoEvento           NVARCHAR(100) NOT NULL,
    ReferenciaLote       INT NULL,
    ReferenciaOrigen     INT NULL,
    ReferenciaInsumo     INT NULL,
    ReferenciaDestino    INT NULL,
    ReferenciaAgronomo   INT NULL,
    Detonante            NVARCHAR(200) NOT NULL,
    PayloadJson          NVARCHAR(MAX) NULL,
    FechaHora            DATETIME NOT NULL
                         CONSTRAINT DF_SistemaBitacora_FechaHora DEFAULT GETDATE(),
    -- Auditoría
    Estado               VARCHAR(1) NOT NULL
                         CONSTRAINT DF_SistemaBitacora_Estado DEFAULT ('A')
                         CONSTRAINT CK_SistemaBitacora_Estado CHECK (Estado IN ('A','X')),
    FechaCreacion        DATETIME NOT NULL
                         CONSTRAINT DF_SistemaBitacora_FechaCreacion DEFAULT GETDATE(),
    FechaModifica        DATETIME NULL,
    IdUsuarioCreacion    INT NULL,
    IdUsuarioModifica    INT NULL,
    -- Relaciones
    CONSTRAINT FK_SistemaBitacora_Lote      FOREIGN KEY (ReferenciaLote)        REFERENCES CultivoLote(IdLote),
    CONSTRAINT FK_SistemaBitacora_Insumo    FOREIGN KEY (ReferenciaInsumo)      REFERENCES CultivoInsumo(IdInsumo),
    CONSTRAINT FK_SistemaBitacora_Agronomo  FOREIGN KEY (ReferenciaAgronomo)    REFERENCES CultivoAgronomo(IdAgronomo)
);
GO

CREATE INDEX IX_GranjaDispositivo_Instalacion   ON GranjaDispositivo(IdInstalacion);
CREATE INDEX IX_CultivoLote_Instalacion         ON CultivoLote(IdInstalacion);
CREATE INDEX IX_CultivoLote_Agronomo            ON CultivoLote(IdAgronomo);
CREATE INDEX IX_CultivoMetrica_Lote             ON CultivoMetrica(IdLote);
CREATE INDEX IX_CultivoMetrica_Dispositivo      ON CultivoMetrica(IdDispositivo);
CREATE INDEX IX_CultivoProduccion_Lote          ON CultivoProduccion(IdLote);
CREATE INDEX IX_CultivoCicloVida_Lote           ON CultivoCicloVida(IdLote);
GO