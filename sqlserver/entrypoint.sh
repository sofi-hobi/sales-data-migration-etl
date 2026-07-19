#!/bin/bash
set -euo pipefail

/opt/mssql/bin/sqlservr &
sqlserver_pid=$!

cleanup() {
    kill -TERM "${sqlserver_pid}" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT

echo "Esperando a que SQL Server acepte conexiones..."
for intento in $(seq 1 60); do
    if /opt/mssql-tools18/bin/sqlcmd \
        -S localhost \
        -U sa \
        -P "${MSSQL_SA_PASSWORD}" \
        -C \
        -Q "SELECT 1" >/dev/null 2>&1; then
        echo "SQL Server está disponible."
        break
    fi

    if ! kill -0 "${sqlserver_pid}" 2>/dev/null; then
        echo "SQL Server terminó inesperadamente."
        wait "${sqlserver_pid}"
        exit 1
    fi

    if [ "${intento}" -eq 60 ]; then
        echo "SQL Server no estuvo disponible dentro del tiempo esperado."
        exit 1
    fi

    sleep 2
done

echo "Ejecutando la inicialización de SmartCleanOrigen..."
/opt/mssql-tools18/bin/sqlcmd \
    -S localhost \
    -U sa \
    -P "${MSSQL_SA_PASSWORD}" \
    -C \
    -b \
    -i /usr/src/app/scripts.sql

echo "Base SmartCleanOrigen inicializada correctamente."
wait "${sqlserver_pid}"
