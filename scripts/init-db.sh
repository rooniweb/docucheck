#!/bin/bash
# Crée la base n8n en plus de la base principale docucheck
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE n8n;
    GRANT ALL PRIVILEGES ON DATABASE n8n TO $POSTGRES_USER;
EOSQL
