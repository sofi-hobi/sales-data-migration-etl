FROM mcr.microsoft.com/mssql/server:2022-latest

USER root
WORKDIR /usr/src/app

COPY sqlserver/entrypoint.sh /usr/src/app/entrypoint.sh
COPY sqlserver/scripts.sql /usr/src/app/scripts.sql
COPY sql/source_schema /usr/src/app/source_schema
COPY data/source /usr/src/app/data

RUN sed -i 's/\r$//' /usr/src/app/entrypoint.sh \
    && chmod +x /usr/src/app/entrypoint.sh \
    && chown -R mssql:root /usr/src/app

USER mssql

ENTRYPOINT ["/bin/bash", "/usr/src/app/entrypoint.sh"]
