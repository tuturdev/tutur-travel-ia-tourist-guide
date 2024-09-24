import json
import boto3
import os
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore, PineconeEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

def lambda_handler(event, context):
    # Parámetros del evento de la API Gateway
    country = event['country']
    city = event['city']
    group = event['group']
    participants = event['participants']
    days = event['days']
    activities = event['activities']

    # Configura Pinecone
    pinecone_api_key = os.environ['PINECONE_API_KEY']
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = "tutur-vector"
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = Pinecone.from_existing_index(index_name, embedding=embeddings)
    
    # Crear el retriever y configurar el LLM
    retriever = vector_store.as_retriever()
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.environ['OPENAI_API_KEY'])
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    
    # Definir el template del prompt
    prompt_template = """
    Imagina que eres un agente de viajes especialista en paseos domésticos por el pais:{country}.
    Diseña un plan de paseo simple en formato JSON para {group} de {participants} que estarán en ciudad:{city} por {days} días.
    Incluye actividades: {activities}.
    """
    
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["country", "city", "group", "participants", "days", "activities"]
    )
    
    formatted_prompt = prompt.format(
        country=country,
        city=city,
        group=group,
        participants=', '.join(participants),
        days=days,
        activities=', '.join(activities)
    )
    
    # Ejecutar el flujo RAG
    result = qa_chain.invoke({"query": formatted_prompt})
    
    # Devolver la respuesta
    return {
        'statusCode': 200,
        'body': json.dumps(result.get('result'))
    }
