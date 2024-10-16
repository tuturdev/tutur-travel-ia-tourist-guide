import psycopg2
from psycopg2 import pool
from app.secrets import get_secret

class Database:
    def __init__(self, db_config):
        # Crear un pool de conexiones para reutilizar las conexiones
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,  # Puedes ajustar el número máximo de conexiones según tus necesidades
            host=db_config['host'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )

    def get_connection(self):
        # Obtener una conexión del pool
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        # Liberar la conexión de vuelta al pool
        self.connection_pool.putconn(conn)

    def close_all_connections(self):
        # Cerrar todas las conexiones cuando la aplicación termina
        self.connection_pool.closeall()

db_secret = get_secret("rds!db-68ff39fd-1e78-4126-b204-763b8e165933")
# Configuración de la base de datos
db_config = {
    'host': 'tutur-rds-pg-itineraries.cjq4e22go12v.us-east-1.rds.amazonaws.com',
    'database': "tutur_itinerary",
    'user': db_secret.get('username'),
    'password': db_secret.get('password')
}

# Crear una instancia de la clase Database
db = Database(db_config)


