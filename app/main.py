from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
import random
from datetime import datetime
from app.utils import get_secret, generate_random_guide_id
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Inicializamos FastAPI
app = FastAPI()

# Reutilización de Pinecone y LangChain
pinecone_client = None
vector_store = None
llm = None
qa_chain = None

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

# Definir el modelo de entrada usando Pydantic para validación
class GuideRequest(BaseModel):
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
        start_time = datetime.now()
        print(f"Inicio del proceso: {start_time}")
        
        # Inicializar servicios si no están inicializados
        service_start_time = datetime.now()
        initialize_services()
        service_end_time = datetime.now()
        print(f"Servicios inicializados en: {(service_end_time - service_start_time).total_seconds()} segundos")
        
        # Convertir fechas a formato legible
        date_parse_start_time = datetime.now()
        try:
            start_dt = datetime.strptime(request.startDatetime, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(request.endDatetime, "%Y-%m-%d %H:%M:%S")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use 'YYYY-MM-DD HH:MM:SS'. {ve}")
        
        formatted_start_datetime = start_dt.strftime("%Y-%m-%d %H:%M:%S")
        formatted_end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S")
        date_parse_end_time = datetime.now()
        print(f"Conversión de fechas tomó: {(date_parse_end_time - date_parse_start_time).total_seconds()} segundos")
        
        # Prepara el texto del prompt
        prompt_start_time = datetime.now()
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
        No incluyas actividades de otros destinos.
        No repitas actividades.

        Datos adicionales:
        Fecha de inicio: {startDatetime}
        Fecha de finalización: {endDatetime}
        Participantes: {participants}

        Para cada lugar del itinerario, proporciona los siguientes datos NO INCLUIR NADA ADICIONAL A ESTOS 4 ATRIBUTOS:
        - PrincipalId
        - Nombre del lugar
        - Descripción breve
        - Coordenadas de latitud y longitud

        El formato de salida debe ser formato json (las claves deben estar en ingles en formato lower camel case) y formateado a utf-8, no incluyas nada adicional que no sea la respuesta.
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
        prompt_end_time = datetime.now()
        print(f"Generación del prompt tomó: {(prompt_end_time - prompt_start_time).total_seconds()} segundos")

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

        # Convertir el texto en objeto JSON
        json_parse_start_time = datetime.now()
        try:
            body = json.loads(output_text)
        except json.JSONDecodeError as e:
            # Imprimir el error y la parte problemática del texto para depuración
            print(f"Error al decodificar JSON: {e}")
            print(f"Texto problemático: {output_text}")
            raise HTTPException(status_code=500, detail=f"Error al decodificar la respuesta JSON: {str(e)}")
        json_parse_end_time = datetime.now()
        print(f"Decodificación de JSON tomó: {(json_parse_end_time - json_parse_start_time).total_seconds()} segundos")
        
        # Generar un código aleatorio para touristGuideId
        tourist_guide_id = generate_random_guide_id()

        # Fin del proceso
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        print(f"Tiempo total del proceso: {total_time} segundos")

        # Devolver la respuesta
        return {
            "touristGuideId": tourist_guide_id,
            "guideDetails": body
        }

    except HTTPException as http_ex:
        raise http_ex  # Relanzar excepciones HTTP ya manejadas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/health")
def health_check():
    return {"status": "ok heath"}
