#!/bin/bash
# Iniciar SQL Server en segundo plano
/opt/mssql/bin/sqlservr &
pid=$!

# Esperar a que SQL Server esté disponible
echo "Esperando a que SQL Server inicie..."
sleep 25

# Ejecutar el script de inicialización
echo "Ejecutando scripts.sql..."
/opt/mssql-tools18/bin/sqlcmd -S localhost -U SA -P "Your_Password123" -C -i /usr/src/app/scripts.sql

echo "Configuración de SQL Server completada."
# Esperar al proceso de SQL Server para mantener el contenedor activo
wait $pid
