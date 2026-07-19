FROM postgres:15-alpine

# Copiar scripts al directorio de inicialización de Postgres
# Postgres ejecutará automáticamente los scripts .sql en este directorio al iniciar por primera vez
COPY scripts.sql /docker-entrypoint-initdb.d/
