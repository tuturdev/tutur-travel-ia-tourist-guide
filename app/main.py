from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
from datetime import datetime
from app.utils import  insert_itinerary_in_background,generate_unique_id
from app.secrets import get_secret
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import boto3
from app.country_code_service import router as country_code_router 
from app.activities_service import router as activities_router
from app.destinations_service import router as destination_router
from typing import Optional
import threading

# Inicializamos FastAPI
app = FastAPI()

# Reutilización de Pinecone y LangChain
pinecone_client = None
vector_store = None
llm = None
qa_chain = None
dynamodb = boto3.client('dynamodb')

def remove_duplicates(principal_ids):
    # Convertir la lista en un conjunto para eliminar duplicados y luego convertir de nuevo a lista
    return list(set(principal_ids))

def query_dynamo(principal_ids):
    try:
        print(f"Data input: {principal_ids}")
        ids = remove_duplicates(principal_ids)
        print(f"Data sin duplicados: {ids}")
        # Preparar la estructura de Keys para batch_get_item
        keys = [{'principalId': {'S': principal_id}} for principal_id in ids]

       
        
        # Realizar la consulta en batch
        response = dynamodb.batch_get_item(
            RequestItems={
                'tutur-activities': {
                    'Keys': keys,
                    'ProjectionExpression': 'principalId, description,location_lat,location_lng,totalScore, reviewsCount, estimated_time, opening_hours, s3Images'
                }
            }
        )
        
        # Procesar los resultados
        items = response.get('Responses', {}).get('tutur-activities', [])
        
        # Formatear los resultados
        result = []
        for item in items:
            # Extraer los datos de s3Images si existen
            s3_images = item.get('s3Images', {}).get('M', {})  # Acceder al mapa dentro de s3Images
            
            formatted_item = {
                'principalId': item['principalId']['S'],
                'description': item.get('description', {}).get('S', ''),
                'coordinates': {
                    'latitude':float(item.get('location_lat', {}).get('N', 0.0)),
                    'longitude':float(item.get('location_lng', {}).get('N', 0.0))
                },
                'totalScore': float(item.get('totalScore', {}).get('N', 0.0)),
                'reviewsCount': int(item.get('reviewsCount', {}).get('N', 0)),
                'estimated_time': item.get('estimated_time', {}).get('S', ''),
                'opening_hours': item.get('opening_hours', {}).get('S', ''),
                's3Images': {
                    's3MainImageUrl': s3_images.get('s3MainImageUrl', {}).get('S', ''),
                    's3DetailImageUrl': s3_images.get('s3DetailImageUrl', {}).get('S', ''),
                    's3ExpandImageUrl': s3_images.get('s3ExpandImageUrl', {}).get('S', '')
                }
            }
            result.append(formatted_item)
        
        return result
    
    except Exception as e:
        print(f"Error al consultar DynamoDB: {str(e)}")
        return None



def initialize_services():
    global pinecone_client, vector_store, llm, qa_chain
    if not pinecone_client:
        # Obtener secretos solo una vez
        pinecone_secrets = get_secret("pinecone-tutur-test")
        openai_secrets = get_secret("gpt-tutur-test")
        
        pinecone_api_key = pinecone_secrets.get('api-key')
        openai_api_key = openai_secrets.get('api-key')

        pinecone_client = Pinecone(api_key=pinecone_api_key)
        index = pinecone_client.Index("tutur-vector")
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
        vector_store = PineconeVectorStore(index=index, embedding=embeddings)
        
        retriever = vector_store.as_retriever()
        llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=openai_api_key)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )

# Función para hacer el merge de los datos de DynamoDB con las actividades del itinerario
def merge_activity_data(itinerary, dynamo_dict):
    for day in itinerary:
        # Filtrar las actividades que tienen un match en dynamo_dict
        day['activities'] = [
            activity for activity in day['activities']
            if activity['principalId'] in dynamo_dict
        ]
        
        # Actualizar las actividades que hacen match
        for activity in day['activities']:
            principal_id = activity['principalId']
            if principal_id in dynamo_dict:
                activity.update({
                    'totalScore': dynamo_dict[principal_id].get('totalScore', 0.0),
                    'reviewsCount': dynamo_dict[principal_id].get('reviewsCount', 0),
                    'estimated_time': dynamo_dict[principal_id].get('estimated_time', ''),
                    'description': dynamo_dict[principal_id].get('description', ''),
                    'coordinates': dynamo_dict[principal_id].get('coordinates', []),
                    'opening_hours': dynamo_dict[principal_id].get('opening_hours', ''),
                    's3Images': dynamo_dict[principal_id].get('s3Images', {})
                })
    return itinerary


# Definir el modelo de entrada usando Pydantic para validación
class GuideRequest(BaseModel):
    clientId: Optional[str] = Field(None, description="Optional client ID")
    country: str = Field(..., description="Country for the itinerary")
    city: str = Field(..., description="City for the itinerary")
    group: str = Field(..., description="Group for the itinerary")
    participants: dict = Field(..., description="Participants information")
    activities: list = Field(..., description="List of activities for the itinerary")
    startDatetime: str = Field(..., description="Start datetime in format YYYY-MM-DD HH:MM:SS")
    endDatetime: str = Field(..., description="End datetime in format YYYY-MM-DD HH:MM:SS")
    

@app.post("/generate-guide")
def generate_guide(request: GuideRequest):
    try:
              
        initialize_services()
                
        try:
            start_dt = datetime.strptime(request.startDatetime, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(request.endDatetime, "%Y-%m-%d %H:%M:%S")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use 'YYYY-MM-DD HH:MM:SS'. {ve}")
        
        formatted_start_datetime = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        formatted_end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S")
 
        participants_text = ', '.join([f"{key}: {value}" for key, value in request.participants.items()])
        activities_text = ', '.join(request.activities)

        prompt_template = """
        Actúa como un asistente de viajes especializado en turismo familiar en {city}, {country}. 
        Tu objetivo es generar un itinerario turístico personalizado para un grupo familiar compuesto por {participants}. 
        Las actividades deben ser de estas categorias: {activities} y el itinerario se desarrollará entre {startDatetime} y {endDatetime}. 
        A continuación se detallan las reglas que debes seguir:

        Proporciona lugares exclusivamente dentro del destino {city} ESTO ES OBLIGATORIO.
        Todos los lugares seleccionados deben coincidir con la necesidad de actividad solicitada: {activities}.
        Asegúrate de que los lugares estén abiertos en las fechas y horas seleccionadas, respetando los horarios de apertura y cierre de cada lugar.
        El tiempo total de todas las actividades en un día debe ser menor o igual a 10 horas. Usa el tiempo estimado de cada actividad para realizar este cálculo.
        Determina el lugar que más se ajusta a las respuestas del formulario en términos de popularidad, reseñas, y adecuación para el grupo familiar (TOP 1).
        La distancia entre cada actividad seleccionada no debe exceder los 5 km lineales.
        El itinerario debe estar segmentado por día iniciando de 1 a N.
        Si no hay actividades suficientes que cumplan con todos los requisitos, ajusta las opciones cercanas dentro del destino {city}, 
        pero siempre asegúrate de que la suma de tiempo sea menor o igual a las 10 horas diarias y que los lugares estén abiertos en los horarios indicados.
        Si todavía queda tiempo que cubrir, no lo hagas; deja la guía hasta ese punto.
        No incluyas actividades de otras ciudades diferentes a {city}.
        No repitas actividades.

        Datos adicionales:
        Fecha de inicio: {startDatetime}
        Fecha de finalización: {endDatetime}
        Participantes: {participants}

        Para cada lugar del itinerario, proporciona los siguientes datos NO INCLUIR NADA ADICIONAL A ESTOS 4 ATRIBUTOS:
        - Id unico o PrincipalId (este campo es mandatorio y debe salir de la base de conocimientos no autogeneres ni te inventes) y el nombre de esta eqtiqueta simepre debe ser principalId
        - Nombre del lugar (este campo es mandatorio y debe salir de la base de conocimientos no autogeneres ni te inventes)y el nombre de esta eqtiqueta simepre debe ser name

        El formato de salida debe ser formato json (las claves deben estar en ingles en formato lower camel case) y formateado a utf-8 y todo debe ser envuelto en un objeto padre llamado itinerary que sera un array de los días, no incluyas nada adicional que no sea la respuesta.
        """

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["country", "city", "participants", "activities", "startDatetime", "endDatetime"]
        )

        formatted_prompt = prompt.format(
            country=request.country,
            city=request.city,
            participants=participants_text,
            activities=activities_text,
            startDatetime=formatted_start_datetime,
            endDatetime=formatted_end_datetime
        )
        # Ejecutar el flujo de QA
        qa_start_time = datetime.now()
        result = qa_chain.invoke({"query": formatted_prompt})
        qa_end_time = datetime.now()
        print(f"Tiempo de ejecución del flujo QA: {(qa_end_time - qa_start_time).total_seconds()} segundos")

        output_text = result.get('result', '')

        if not output_text.strip():
            raise HTTPException(status_code=500, detail="Empty response from the model.")
        
        # Remover cualquier contenido adicional que no sea JSON
        output_text = output_text.strip()

        # Remover la posible envoltura de markdown y caracteres extraños
        if output_text.startswith("```json"):
            output_text = output_text[7:-3].strip()  # Eliminar los delimitadores "```json"

        try:
            body = json.loads(output_text)

        except json.JSONDecodeError as e:
            # Imprimir el error y la parte problemática del texto para depuración
            print(f"Error al decodificar JSON: {e}")
            print(f"Texto problemático: {output_text}")
            raise HTTPException(status_code=500, detail=f"Error al decodificar la respuesta JSON: {str(e)}")
        
        print(f"respuesta IA:{body}")
        # Usar una list comprehension para extraer todos los 'principalId'
        principal_ids = [
            activity['principalId']
            for day in body['itinerary']
            for activity in day['activities']
            if 'principalId' in activity  # Verificamos si 'principalId' existe
        ]
        db_response = query_dynamo(principal_ids)
        # Verificar si db_response es None
        if db_response is None:
            raise HTTPException(status_code=500, detail="Error al consultar DynamoDB o no se encontraron resultados.")
        # Crear un diccionario de acceso rápido con principalId como clave
        dynamo_dict = {item['principalId']: item for item in db_response}
        # Hacer el merge de los datos de DynamoDB con el itinerario
        merged_itinerary = merge_activity_data(body['itinerary'], dynamo_dict)
        body['itinerary'] = merged_itinerary
        # Generar un código aleatorio para touristGuideId
        db_start_time = datetime.now()
        tourist_guide_id = generate_unique_id()
        thread = threading.Thread(target=insert_itinerary_in_background, args=(tourist_guide_id,request.clientId, body))
        thread.start() 
        db_end_time = datetime.now()
        print(f"Tiempo de ejecución alamcenamiento de la bd: {(db_end_time - db_start_time).total_seconds()} segundos")

        # Devolver la respuesta
        return {
            "touristGuideId": tourist_guide_id,
            "guideDetails": body
        }

    except HTTPException as http_ex:
        raise http_ex  # Relanzar excepciones HTTP ya manejadas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(country_code_router, prefix="/v1/tutur/info")
app.include_router(activities_router, prefix="/v1/tutur/info")
app.include_router(destination_router, prefix="/v1/tutur/info")
@app.get("/health")
def health_check():
    return {"status": "ok heath"}
