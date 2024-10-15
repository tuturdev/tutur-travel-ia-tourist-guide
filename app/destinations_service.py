from fastapi import APIRouter, HTTPException
import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel

# Crear un router para este módulo
router = APIRouter()

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('tutur-activities')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError

class DestinationRequest(BaseModel):
    destinationId: str

@router.get("/all-destinations")
def get_unique_combinations():
    try:
        # Escanear todos los registros con `destinationId`, `city`, y `countryCode`
        response = table.scan(
            ProjectionExpression='destinationId, city, countryCode'
        )
        
        # Usar un conjunto para asegurarse de que solo se mantengan combinaciones únicas
        unique_items = set()
        
        for item in response['Items']:
            # Crear una tupla de los valores únicos y agregarla al conjunto
            unique_items.add((item['destinationId'], item.get('city', None), item['countryCode']))
        
        # Convertir el conjunto en una lista de diccionarios para devolver en la respuesta
        unique_items_list = [
            {'destinationId': destinationId, 'city': city, 'countryCode': countryCode}
            for destinationId, city, countryCode in unique_items
        ]
        
        return {'uniqueItems': unique_items_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")
    
@router.post("/activities-by-destination")
def get_activities_by_destination(request: DestinationRequest):
    try:
        # Obtener el destinationId del cuerpo de la solicitud
        destinationId = request.destinationId
        
        # Verificar que se proporcionó el destinationId
        if not destinationId:
            raise HTTPException(status_code=400, detail="destinationId is required")

        # Consultar todos los registros por `destinationId`
        response = table.query(
            KeyConditionExpression=Key('destinationId').eq(destinationId),
            IndexName='DestinationIdIndex'
        )
        
        # Si no hay registros, devolver un error
        if 'Items' not in response or len(response['Items']) == 0:
            raise HTTPException(status_code=404, detail="No records found")

        # Devolver la respuesta, manejando los objetos Decimal
        items = json.loads(json.dumps(response['Items'], default=decimal_default))
        
        return {'activities': items}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")