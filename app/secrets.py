import boto3
import json

def get_secret(secret_name):
    # Especifica la región
    region_name = "us-east-1"  # Cambia a la región donde están tus secretos de AWS

    client = boto3.client('secretsmanager', region_name=region_name)
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except Exception as e:
        raise Exception(f"Error getting secret: {e}")
