FROM mcr.microsoft.com/mssql/server:2022-latest

USER root
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY scripts.sql /usr/src/app/
COPY entrypoint.sh /usr/src/app/

RUN chmod +x /usr/src/app/entrypoint.sh

USER mssql

ENTRYPOINT ["/bin/bash", "/usr/src/app/entrypoint.sh"]
