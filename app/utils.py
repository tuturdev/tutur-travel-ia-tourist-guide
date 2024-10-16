import json
from app.db import db
import datetime

def generate_unique_id():
    try:
        # Obtener la conexión del pool
        conn = db.get_connection()
        cursor = conn.cursor()

        # Obtener el siguiente valor de la secuencia
        cursor.execute("SELECT nextval('iti.tutur_seq_itinerary_id');")
        next_sequence = cursor.fetchone()[0]

        # Obtener la fecha juliana en formato YYDDD (5 dígitos)
        current_date = datetime.datetime.now().strftime('%y%j')

        # Combinar la fecha juliana con la secuencia para formar el ID de 16 dígitos
        unique_id = f"{current_date}{str(next_sequence).zfill(11)}"

        return unique_id

    except Exception as e:
        print(f"Error al generar el ID único: {e}")
        return None

    finally:
        # Liberar la conexión al pool
        db.release_connection(conn)


def insert_itinerary(client_id, client_itinerary):
    try:
        # Obtener el ID único generado
        itinerary_id = generate_unique_id()

        # Obtener la conexión del pool
        conn = db.get_connection()
        cursor = conn.cursor()

        # Insertar el itinerario en la tabla
        insert_query = """
        INSERT INTO iti.client_itineraries (id, client_id, client_itinerary, created_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP);
        """
        cursor.execute(insert_query, (itinerary_id, client_id, json.dumps(client_itinerary)))

        # Hacer commit de la transacción
        conn.commit()

        return itinerary_id  # Devolver el ID generado

    except Exception as e:
        print(f"Error al insertar el itinerario: {e}")
        return None

    finally:
        # Liberar la conexión al pool
        db.release_connection(conn)

def insert_itinerary_in_background(itinerary_id,client_id, client_itinerary):
    conn = db.get_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO iti.client_itineraries (id, client_id, client_itinerary, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP);
            """
            cursor.execute(query, (itinerary_id,client_id, json.dumps(client_itinerary)))
            conn.commit()
    finally:
        db.release_connection(conn)


