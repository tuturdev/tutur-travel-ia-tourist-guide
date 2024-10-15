from fastapi import APIRouter, HTTPException
import boto3
import json
from decimal import Decimal

# Crear un router para este módulo
router = APIRouter()

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
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
