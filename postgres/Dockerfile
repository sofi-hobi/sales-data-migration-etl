FROM postgres:15-alpine

# Copiar scripts al directorio de inicialización de Postgres.
# Postgres ejecutará automáticamente los scripts .sql en este directorio
# al iniciar por primera vez, en orden alfabético:
#   001_postgres_ddl.sql   -> crea las tablas de negocio
#   002_audit_tables.sql   -> crea las tablas de auditoría
COPY 001_postgres_ddl.sql /docker-entrypoint-initdb.d/
COPY 002_audit_tables.sql /docker-entrypoint-initdb.d/
