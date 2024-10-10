import boto3
import json
import random

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

def generate_random_guide_id():
    return ''.join([str(random.randint(0, 9)) for _ in range(16)])
