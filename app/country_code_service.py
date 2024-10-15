from fastapi import APIRouter, HTTPException
import boto3
import json

# Crear un router para este módulo
router = APIRouter()

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('tutur-activities')

@router.get("/country-codes")
def get_country_codes():
    try:
        # Consultar usando el GSI de countryCode
        response = table.scan(
            IndexName='CountryCodeIndex',
            ProjectionExpression='countryCode'
        )
        
        # Obtener los códigos únicos de país
        country_codes = set([item['countryCode'] for item in response['Items']])
        
        return {'countryCodes': list(country_codes)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar DynamoDB: {str(e)}")
