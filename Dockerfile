FROM postgres:15-alpine

# Copiar TODOS los scripts .sql de esta carpeta al directorio de
# inicializacion de Postgres. Postgres los ejecuta automaticamente,
# en orden alfabetico, la primera vez que arranca el contenedor
# (cuando el volumen postgres_data esta vacio).
#
# El orden alfabetico es intencional:
#   001_postgres_ddl.sql   -> crea las tablas de negocio
#   002_audit_tables.sql   -> crea las tablas de auditoria
COPY *.sql /docker-entrypoint-initdb.d/
