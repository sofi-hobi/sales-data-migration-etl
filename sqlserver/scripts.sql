-- Archivo de compatibilidad con la estructura original del repositorio.
-- Ejecutar con sqlcmd para que las directivas :r sean reconocidas.
:ON ERROR EXIT
:r /usr/src/app/source_schema/01_create_tables.sql
:r /usr/src/app/source_schema/02_create_procedures.sql
:r /usr/src/app/source_schema/03_create_views.sql
:r /usr/src/app/source_schema/04_load_json.sql
