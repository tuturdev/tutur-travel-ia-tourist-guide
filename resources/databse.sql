-- Crear la base de datos llamada TUTUR_ITINERARY
CREATE DATABASE TUTUR_ITINERARY
    WITH OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;


-- Crear un esquema llamado iti dentro de la base de datos TUTUR_ITINERARY
CREATE SCHEMA iti;

-- Establecer el esquema iti como el esquema predeterminado para la sesión
SET search_path TO iti;

-- Crear la secuencia dentro del esquema iti (para generar IDs únicos)
CREATE SEQUENCE iti.tutur_seq_itinerary_id
    START 1
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 99999999999  -- Hasta 11 dígitos
    CACHE 1
    
CREATE TABLE iti.client_itineraries (
    id VARCHAR(16) PRIMARY KEY,        -- ID único de 16 caracteres
    client_id VARCHAR(255),   -- ID del cliente
    client_itinerary JSONB NOT NULL,   -- Itinerario en formato JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Timestamp de creación
);
