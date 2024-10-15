from fastapi import APIRouter, HTTPException, Query
import boto3
import json
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel
from typing import List

# Crear un router para este módulo
router = APIRouter()

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('tutur-activities')

# Función para convertir objetos Decimal a tipos serializables por JSON
def decimal_default(obj):
    if isinstance(obj, Decimal):
        # Convertir a entero o flotante según el caso
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError

class ActivityRequest(BaseModel):
    principalId: str


class PrincipalIdsRequest(BaseModel):
    principalIds: List[str]  # Usar List en lugar de list


@router.get("/all-activities")
def get_all_activities():
    try:
        # Escanear todos los registros en la tabla
        response = table.scan()
        
        # Convertir los objetos Decimal en la respuesta de DynamoDB
        items = json.loads(json.dumps(response['Items'], default=decimal_default))
        
        return {'activities': items}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")



@router.post("/get-activity")
def get_activity_by_principal_id(request: ActivityRequest):
    try:
        # Obtener el principalId del cuerpo de la solicitud
        principalId = request.principalId
        
        # Verificar que se proporcionó el principalId
        if not principalId:
            raise HTTPException(status_code=400, detail="principalId is required")

        # Realizar la consulta a DynamoDB
        response = table.query(
            KeyConditionExpression=Key('principalId').eq(principalId)
        )
        
        # Si no hay registros, devolver un error
        if 'Items' not in response or len(response['Items']) == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        
        # Devolver el primer registro encontrado, manejando los objetos Decimal
        item = json.loads(json.dumps(response['Items'][0], default=decimal_default))
        
        return {'activity': item}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")
    

@router.post("/activities-by-principal-ids")
def get_activities_by_principal_ids(request: PrincipalIdsRequest):
    try:
        # Obtener los principalIds del cuerpo de la solicitud
        principal_ids = request.principalIds
        
        if not principal_ids:
            raise HTTPException(status_code=400, detail="principalIds list is required")
        
        # Realizar consultas individuales para cada principalId
        result = []
        for pid in principal_ids:
            response = table.get_item(
                Key={
                    'principalId': pid.strip()  # Asegurarse de que principalId es una cadena
                },
                ProjectionExpression='principalId, #name, fees_currency, fees_entrance_fee, fees_reduced_entrance_fee',  # Utilizar alias para name
                ExpressionAttributeNames={
                    "#name": "name"  # Alias para el campo 'name' que es una palabra reservada en DynamoDB
                }
            )
            item = response.get('Item')
            if item:
                # Crear un diccionario con los campos solicitados
                formatted_item = {
                    'principalId': item.get('principalId', ''),
                    'name': item.get('name', ''),
                    'fees_currency': item.get('fees_currency', ''),
                    'fees_entrance_fee': format(float(item.get('fees_entrance_fee', 0)), '.2f') if item.get('fees_entrance_fee') else '0.00',
                    'fees_reduced_entrance_fee': format(float(item.get('fees_reduced_entrance_fee', 0)), '.2f') if item.get('fees_reduced_entrance_fee') else '0.00'
                }
                result.append(formatted_item)
        
        if not result:
            raise HTTPException(status_code=404, detail="No records found for the provided principalIds")
        
        # Devolver los resultados en formato JSON
        return {'activities': result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")